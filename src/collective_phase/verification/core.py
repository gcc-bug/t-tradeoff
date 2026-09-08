from __future__ import annotations

from dataclasses import asdict, dataclass
import cmath
import math
import random

import numpy as np

from ..circuit import Candidate, Operation


@dataclass(frozen=True)
class VerificationResult:
    status: str
    checked_basis_states: int
    max_phase_error: float | None
    data_restored: bool
    workspace_restored: bool
    diagonal_permutation_structure: bool
    dense_check: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _phase_distance(first: float, second: float) -> float:
    return abs(cmath.exp(1j * first) - cmath.exp(1j * second))


def _apply_basis_operation(
    bits: list[int], phase: float, operation: Operation, angle_map
) -> float:
    kind = operation.kind
    if kind == "x":
        bits[operation.qubits[0]] ^= 1
    elif kind == "cx":
        control, target = operation.qubits
        bits[target] ^= bits[control]
    elif kind in {"toffoli", "and_compute", "and_uncompute"}:
        first, second, target = operation.qubits
        bits[target] ^= bits[first] & bits[second]
    elif kind in {"hwp_compute", "hwp_uncompute"}:
        control_count = int(operation.payload["control_count"])
        weight_count = int(operation.payload["weight_count"])
        controls = operation.qubits[:control_count]
        targets = operation.qubits[control_count : control_count + weight_count]
        weight = sum(bits[qubit] for qubit in controls)
        for index, target in enumerate(targets):
            bits[target] ^= (weight >> index) & 1
    elif kind == "phase":
        if bits[operation.qubits[0]]:
            phase += angle_map[operation.angle_id].scaled(operation.multiplier).radians
    elif kind == "phase_gradient":
        value = sum(bits[qubit] << index for index, qubit in enumerate(operation.qubits))
        phase += angle_map[operation.angle_id].scaled(operation.multiplier).radians * value
    else:
        raise ValueError(f"unsupported semantic operation {kind!r}")
    return phase


def simulate_basis(candidate: Candidate, x: int) -> tuple[int, tuple[int, ...], float]:
    n = candidate.program.qubit_count
    bits = [(x >> index) & 1 for index in range(n)] + [0] * candidate.workspace_qubits
    phase = candidate.global_phase
    angle_map = candidate.program.angle_map
    for operation in candidate.operations:
        phase = _apply_basis_operation(bits, phase, operation, angle_map)
    output = sum(bits[index] << index for index in range(n))
    return output, tuple(bits[n:]), phase


def verify_candidate(candidate: Candidate, max_qubits: int = 10) -> VerificationResult:
    if candidate.status != "success":
        return VerificationResult(
            status="not_run",
            checked_basis_states=0,
            max_phase_error=None,
            data_restored=False,
            workspace_restored=False,
            diagonal_permutation_structure=False,
            dense_check="not_run",
            message=candidate.failure_reason or "candidate did not compile",
        )
    n = candidate.program.qubit_count
    if n > max_qubits:
        return VerificationResult(
            status="certificate_only",
            checked_basis_states=0,
            max_phase_error=None,
            data_restored=False,
            workspace_restored=False,
            diagonal_permutation_structure=True,
            dense_check="not_run",
            message=f"n={n} exceeds exhaustive verification limit n<={max_qubits}",
        )
    max_error = 0.0
    data_restored = True
    workspace_restored = True
    for x in range(1 << n):
        output, workspace, phase = simulate_basis(candidate, x)
        data_restored &= output == x
        workspace_restored &= not any(workspace)
        max_error = max(max_error, _phase_distance(phase, candidate.program.phase_radians(x)))
    success = data_restored and workspace_restored and max_error <= 1e-10
    success_status = (
        "verified_ideal_semantics"
        if candidate.accounting_status == "emitted"
        else "verified_ideal_macro_semantics"
    )
    return VerificationResult(
        status=success_status if success else "verification_failure",
        checked_basis_states=1 << n,
        max_phase_error=max_error,
        data_restored=data_restored,
        workspace_restored=workspace_restored,
        diagonal_permutation_structure=True,
        dense_check="not_run",
        message=(
            "ideal operation-level basis action verified"
            if success and candidate.accounting_status == "emitted"
            else "ideal macro basis action verified"
            if success
            else "basis action mismatch"
        ),
    )


def verify_dense_action(candidate: Candidate, seed: int = 0) -> float:
    """Independently propagate a coherent data state through the ideal operations."""
    if candidate.status != "success":
        raise ValueError("cannot densely verify an unsuccessful candidate")
    total = candidate.program.qubit_count + candidate.workspace_qubits
    if total > 12:
        raise ValueError("dense verification is limited to 12 total qubits")
    data_size = 1 << candidate.program.qubit_count
    full_size = 1 << total
    rng = random.Random(seed)
    amplitudes = np.array(
        [complex(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(data_size)],
        dtype=np.complex128,
    )
    amplitudes /= np.linalg.norm(amplitudes)
    state = np.zeros(full_size, dtype=np.complex128)
    state[:data_size] = amplitudes
    angle_map = candidate.program.angle_map
    for operation in candidate.operations:
        updated = np.zeros_like(state)
        for basis, amplitude in enumerate(state):
            if amplitude == 0:
                continue
            bits = [(basis >> index) & 1 for index in range(total)]
            phase = _apply_basis_operation(bits, 0.0, operation, angle_map)
            target = sum(bit << index for index, bit in enumerate(bits))
            updated[target] += amplitude * cmath.exp(1j * phase)
        state = updated
    state *= cmath.exp(1j * candidate.global_phase)
    expected = np.zeros_like(state)
    expected[:data_size] = np.array(
        [
            amplitudes[x] * cmath.exp(1j * candidate.program.phase_radians(x))
            for x in range(data_size)
        ]
    )
    return float(np.linalg.norm(state - expected))
