from __future__ import annotations

from dataclasses import asdict, dataclass
import cmath
import math

import numpy as np

from ..lowering import GateEvent, LoweredCircuit, MacroEvent


ONE_QUBIT_GATES: dict[str, np.ndarray] = {
    "h": np.array([[1, 1], [1, -1]], dtype=np.complex128) / math.sqrt(2),
    "x": np.array([[0, 1], [1, 0]], dtype=np.complex128),
    "z": np.diag([1, -1]).astype(np.complex128),
    "s": np.diag([1, 1j]).astype(np.complex128),
    "sdg": np.diag([1, -1j]).astype(np.complex128),
    "t": np.diag([1, cmath.exp(1j * math.pi / 4)]).astype(np.complex128),
    "tdg": np.diag([1, cmath.exp(-1j * math.pi / 4)]).astype(np.complex128),
}
SYNTHESIS_GATES = frozenset(ONE_QUBIT_GATES) | {"w"}


@dataclass(frozen=True)
class LoweredVerificationResult:
    status: str
    scope: str
    operator_norm_error: float | None
    synthesis_error_bound: float
    macro_free: bool
    matrix_bytes: int
    memory_cap_bytes: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _single_qubit_matrix(gates: tuple[str, ...]) -> np.ndarray:
    result = np.eye(2, dtype=np.complex128)
    for gate in gates:
        if gate == "w":
            result = cmath.exp(1j * math.pi / 4) * result
        else:
            result = ONE_QUBIT_GATES[gate] @ result
    return result


def _rotation_requests(lowered: LoweredCircuit) -> tuple[list, list]:
    application = []
    for operation in lowered.candidate.operations:
        if operation.kind in {"phase", "phase_gradient"}:
            application.append(
                lowered.candidate.program.angle_map[operation.angle_id].scaled(
                    operation.multiplier
                )
            )
    preparation = []
    for state in lowered.candidate.required_resource_states:
        binding = lowered.candidate.program.angle_map[state["angle_id"]]
        preparation.extend(binding.scaled(int(value)) for value in state["multipliers"])
    return application, preparation


def _validate_rotations(lowered: LoweredCircuit) -> str | None:
    application, preparation = _rotation_requests(lowered)
    pairs = (
        ("application", application, lowered.application_rotations),
        ("preparation", preparation, lowered.preparation_rotations),
    )
    for label, requests, results in pairs:
        if len(requests) != len(results):
            return f"{label} rotation count mismatch"
        for request, result in zip(requests, results, strict=True):
            if result.angle_key != request.cache_key:
                return f"{label} rotation identity mismatch"
            numeric = (
                result.tolerance,
                result.actual_operator_error,
                result.requested_error,
                result.circuit_global_phase,
            )
            if not all(math.isfinite(value) for value in numeric):
                return f"{label} rotation contains a non-finite value"
            if result.tolerance <= 0 or result.requested_error <= 0:
                return f"{label} rotation has a nonpositive tolerance"
            if result.actual_operator_error < 0:
                return f"{label} rotation has a negative error"
            if set(result.gates) - SYNTHESIS_GATES:
                return f"{label} rotation contains an unsupported gate"
            if result.t_count != sum(gate in {"t", "tdg"} for gate in result.gates):
                return f"{label} rotation T-count mismatch"
            cliffords = sum(gate not in {"t", "tdg", "w"} for gate in result.gates)
            if result.clifford_count != cliffords:
                return f"{label} rotation Clifford-count mismatch"
            actual = _single_qubit_matrix(result.gates)
            if result.exact:
                target = np.diag([1, cmath.exp(1j * request.radians)])
            else:
                actual *= cmath.exp(1j * result.circuit_global_phase)
                target = np.diag(
                    [
                        cmath.exp(-1j * request.radians / 2),
                        cmath.exp(1j * request.radians / 2),
                    ]
                )
            recomputed = float(np.linalg.norm(target - actual, ord=2))
            if abs(recomputed - result.actual_operator_error) > 1e-10:
                return f"{label} rotation operator error mismatch"
            if recomputed > result.requested_error * (1 + 1e-7):
                return f"{label} rotation exceeds its requested error"
    return None


def _validate_events(lowered: LoweredCircuit) -> str | None:
    total_qubits = (
        lowered.candidate.program.qubit_count + lowered.candidate.workspace_qubits
    )
    for event in lowered.events:
        if isinstance(event, MacroEvent):
            if any(
                value < 0
                for value in (
                    event.t_count,
                    event.t_depth,
                    event.measurement_count,
                    event.adaptive_rounds,
                )
            ):
                return "macro event contains a negative resource value"
            continue
        if not isinstance(event, GateEvent):
            return "unknown lowered event type"
        expected_arity = 2 if event.kind == "cx" else 1
        if event.kind not in ONE_QUBIT_GATES and event.kind != "cx":
            return f"unsupported emitted gate {event.kind!r}"
        if len(event.qubits) != expected_arity or len(set(event.qubits)) != expected_arity:
            return f"invalid wires for emitted gate {event.kind!r}"
        if any(qubit < 0 or qubit >= total_qubits for qubit in event.qubits):
            return f"out-of-range wire for emitted gate {event.kind!r}"
    return None


def _apply_one_qubit(
    state: np.ndarray, matrix: np.ndarray, qubit: int
) -> None:
    indices = np.arange(state.shape[0], dtype=np.int64)
    zeros = indices[(indices & (1 << qubit)) == 0]
    ones = zeros | (1 << qubit)
    zero_values = state[zeros].copy()
    one_values = state[ones].copy()
    state[zeros] = matrix[0, 0] * zero_values + matrix[0, 1] * one_values
    state[ones] = matrix[1, 0] * zero_values + matrix[1, 1] * one_values


def _apply_cx(state: np.ndarray, control: int, target: int) -> None:
    indices = np.arange(state.shape[0], dtype=np.int64)
    left = indices[
        ((indices & (1 << control)) != 0) & ((indices & (1 << target)) == 0)
    ]
    right = left | (1 << target)
    values = state[left].copy()
    state[left] = state[right]
    state[right] = values


def _dense_isometry_error(lowered: LoweredCircuit) -> float:
    data_qubits = lowered.candidate.program.qubit_count
    total_qubits = data_qubits + lowered.candidate.workspace_qubits
    data_size = 1 << data_qubits
    full_size = 1 << total_qubits
    difference = np.zeros((full_size, data_size), dtype=np.complex128)
    columns = np.arange(data_size)
    difference[columns, columns] = 1
    for event in lowered.events:
        assert isinstance(event, GateEvent)
        if event.kind == "cx":
            _apply_cx(difference, event.qubits[0], event.qubits[1])
        else:
            _apply_one_qubit(difference, ONE_QUBIT_GATES[event.kind], event.qubits[0])
    difference *= cmath.exp(
        1j * (lowered.candidate.global_phase + lowered.lowering_global_phase)
    )
    for x in range(data_size):
        difference[x, x] -= cmath.exp(
            1j * lowered.candidate.program.phase_radians(x)
        )
    return float(np.linalg.norm(difference, ord=2))


def verify_lowered_circuit(
    lowered: LoweredCircuit,
    total_error: float,
    *,
    memory_cap_bytes: int = 32 * 1024 * 1024,
) -> LoweredVerificationResult:
    """Verify an emitted Clifford+T stream without using the ideal interpreter."""
    if not math.isfinite(total_error) or total_error <= 0:
        raise ValueError("total error must be finite and positive")
    if memory_cap_bytes <= 0:
        raise ValueError("memory cap must be positive")
    numeric = (
        lowered.candidate.global_phase,
        lowered.lowering_global_phase,
        lowered.error_bound,
    )
    if not all(math.isfinite(value) for value in numeric):
        message = "lowered circuit contains a non-finite phase or error"
        return LoweredVerificationResult(
            "verification_failure", "validation", None, lowered.error_bound,
            False, 0, memory_cap_bytes, message
        )
    event_error = _validate_events(lowered)
    if event_error:
        return LoweredVerificationResult(
            "verification_failure", "validation", None, lowered.error_bound,
            False, 0, memory_cap_bytes, event_error
        )
    rotation_error = _validate_rotations(lowered)
    if rotation_error:
        return LoweredVerificationResult(
            "verification_failure", "validation", None, lowered.error_bound,
            not any(isinstance(event, MacroEvent) for event in lowered.events),
            0, memory_cap_bytes, rotation_error
        )
    recomputed_bound = sum(
        result.actual_operator_error for result in lowered.preparation_rotations
    ) + int(lowered.candidate.parameters.get("reuse_count", 1)) * sum(
        result.actual_operator_error for result in lowered.application_rotations
    )
    if abs(recomputed_bound - lowered.error_bound) > 1e-12:
        return LoweredVerificationResult(
            "verification_failure", "validation", None, recomputed_bound,
            False, 0, memory_cap_bytes, "stored synthesis-error bound mismatch"
        )
    if recomputed_bound > total_error * (1 + 1e-7):
        return LoweredVerificationResult(
            "verification_failure", "validation", None, recomputed_bound,
            False, 0, memory_cap_bytes, "synthesis-error budget exceeded"
        )
    macro_free = not any(isinstance(event, MacroEvent) for event in lowered.events)
    if not macro_free:
        return LoweredVerificationResult(
            "macro_not_verified", "ideal_macro_only", None, recomputed_bound,
            False, 0, memory_cap_bytes,
            "macro events are excluded from emitted-circuit verification",
        )
    data_size = 1 << lowered.candidate.program.qubit_count
    full_size = 1 << (
        lowered.candidate.program.qubit_count + lowered.candidate.workspace_qubits
    )
    matrix_bytes = full_size * data_size * np.dtype(np.complex128).itemsize
    allocation_estimate = 3 * matrix_bytes
    if allocation_estimate > memory_cap_bytes:
        return LoweredVerificationResult(
            "verified_lowered_compositional",
            "emitted_replay_and_compositional_error",
            None,
            recomputed_bound,
            True,
            matrix_bytes,
            memory_cap_bytes,
            "dense isometry skipped because its preflight estimate exceeds the memory cap",
        )
    error = _dense_isometry_error(lowered)
    if not math.isfinite(error) or error > total_error * (1 + 1e-7) + 1e-10:
        return LoweredVerificationResult(
            "verification_failure", "clean_input_isometry_spectral_norm", error,
            recomputed_bound, True, matrix_bytes, memory_cap_bytes,
            "lowered clean-input isometry differs from the target",
        )
    return LoweredVerificationResult(
        "verified_lowered_dense",
        "clean_input_isometry_spectral_norm",
        error,
        recomputed_bound,
        True,
        matrix_bytes,
        memory_cap_bytes,
        "emitted stream and clean-input isometry verified",
    )
