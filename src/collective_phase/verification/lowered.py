from __future__ import annotations

from dataclasses import asdict, dataclass
import cmath
from functools import lru_cache
import math

import numpy as np

from ..lowering import GateEvent, LoweredCircuit, MacroEvent
from .core import verify_candidate


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


def _allocated_tolerances(
    lowered: LoweredCircuit, total_error: float
) -> tuple[float, float]:
    application, preparation = _rotation_requests(lowered)
    app_generic = sum(not angle.is_exact_clifford_t for angle in application)
    prep_generic = sum(not angle.is_exact_clifford_t for angle in preparation)
    reuse = int(lowered.candidate.parameters.get("reuse_count", 1))
    if reuse < 1:
        raise ValueError("rotation reuse count must be positive")
    if prep_generic and app_generic:
        return (
            total_error / (2 * app_generic * reuse),
            total_error / (2 * prep_generic),
        )
    if app_generic:
        return total_error / (app_generic * reuse), total_error
    if prep_generic:
        return total_error, total_error / prep_generic
    return total_error, total_error


def _validate_rotations(lowered: LoweredCircuit, total_error: float) -> str | None:
    application, preparation = _rotation_requests(lowered)
    try:
        app_tolerance, prep_tolerance = _allocated_tolerances(lowered, total_error)
    except ValueError as exc:
        return str(exc)
    pairs = (
        ("application", application, lowered.application_rotations, app_tolerance),
        ("preparation", preparation, lowered.preparation_rotations, prep_tolerance),
    )
    for label, requests, results, allocated_tolerance in pairs:
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
            if not math.isclose(
                result.tolerance, allocated_tolerance, rel_tol=1e-12, abs_tol=1e-15
            ):
                return (
                    f"{label} rotation tolerance does not match the "
                    "whole-circuit allocation"
                )
            if not math.isclose(
                result.requested_error,
                allocated_tolerance,
                rel_tol=1e-12,
                abs_tol=1e-15,
            ):
                return (
                    f"{label} rotation requested error does not match its allocation"
                )
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
    declared_qubits = (
        lowered.candidate.program.qubit_count + lowered.candidate.workspace_qubits
    )
    total_qubits = lowered.allocated_qubits or declared_qubits
    if not lowered.candidate.program.qubit_count <= total_qubits <= declared_qubits:
        return "allocated qubits must include data and fit the declared circuit"
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
        if (
            len(event.qubits) != expected_arity
            or len(set(event.qubits)) != expected_arity
        ):
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


TOFFOLI_DECOMPOSITION = (
    GateEvent("h", (2,)),
    GateEvent("cx", (1, 2)),
    GateEvent("tdg", (2,)),
    GateEvent("cx", (0, 2)),
    GateEvent("t", (2,)),
    GateEvent("cx", (1, 2)),
    GateEvent("tdg", (2,)),
    GateEvent("cx", (0, 2)),
    GateEvent("t", (1,)),
    GateEvent("t", (2,)),
    GateEvent("h", (2,)),
    GateEvent("cx", (0, 1)),
    GateEvent("t", (0,)),
    GateEvent("tdg", (1,)),
    GateEvent("cx", (0, 1)),
)


@lru_cache(maxsize=1)
def _toffoli_decomposition_error() -> float:
    actual = np.eye(8, dtype=np.complex128)
    for event in TOFFOLI_DECOMPOSITION:
        if event.kind == "cx":
            _apply_cx(actual, event.qubits[0], event.qubits[1])
        else:
            _apply_one_qubit(actual, ONE_QUBIT_GATES[event.kind], event.qubits[0])
    target = np.eye(8, dtype=np.complex128)
    target[[3, 7], :] = target[[7, 3], :]
    return float(np.linalg.norm(target - actual, ord=2))


def _toffoli_events(qubits: tuple[int, ...]) -> list[GateEvent]:
    first, second, target = qubits
    mapping = {0: first, 1: second, 2: target}
    return [
        GateEvent(event.kind, tuple(mapping[qubit] for qubit in event.qubits))
        for event in TOFFOLI_DECOMPOSITION
    ]


def _expected_emitted_stream(
    lowered: LoweredCircuit,
) -> tuple[list[GateEvent] | None, float, str | None]:
    expected: list[GateEvent] = []
    expected_phase = 0.0
    rotations = iter(lowered.application_rotations)
    for operation in lowered.candidate.operations:
        if operation.kind in {"x", "cx"}:
            expected.append(GateEvent(operation.kind, operation.qubits))
        elif operation.kind in {"toffoli", "and_compute", "and_uncompute"}:
            if (
                lowered.candidate.model_profile != "unitary_clifford_t"
                and operation.kind != "toffoli"
            ):
                return (
                    None,
                    expected_phase,
                    "measurement-assisted primitives lack channel evidence",
                )
            expected.extend(_toffoli_events(operation.qubits))
        elif operation.kind == "phase":
            try:
                synthesis = next(rotations)
            except StopIteration:
                return (
                    None,
                    expected_phase,
                    "event binding ran out of rotation evidence",
                )
            for gate in synthesis.gates:
                if gate == "w":
                    expected_phase += math.pi / 4
                else:
                    expected.append(GateEvent(gate, (operation.qubits[0],)))
            if not synthesis.exact:
                request = lowered.candidate.program.angle_map[
                    operation.angle_id
                ].scaled(operation.multiplier)
                expected_phase += synthesis.circuit_global_phase + request.radians / 2
        else:
            return (
                None,
                expected_phase,
                f"primitive {operation.kind!r} lacks emitted evidence",
            )
    try:
        next(rotations)
    except StopIteration:
        pass
    else:
        return (
            None,
            expected_phase,
            "event binding did not consume all rotation evidence",
        )
    return expected, expected_phase, None


def _dense_isometry_error(lowered: LoweredCircuit) -> float:
    data_qubits = lowered.candidate.program.qubit_count
    total_qubits = lowered.allocated_qubits or (
        data_qubits + lowered.candidate.workspace_qubits
    )
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
    rotation_error = _validate_rotations(lowered, total_error)
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
    if lowered.error_metric != "operator_norm_telescoping":
        return LoweredVerificationResult(
            "lowered_evidence_unsupported", "error_contract", None, recomputed_bound,
            True, 0, memory_cap_bytes, "unsupported whole-circuit error metric",
        )
    if _toffoli_decomposition_error() > 1e-10:
        return LoweredVerificationResult(
            "verification_failure", "primitive_decomposition", None, recomputed_bound,
            True, 0, memory_cap_bytes, "independent Toffoli decomposition check failed",
        )
    ideal = verify_candidate(lowered.candidate)
    if ideal.status != "verified_ideal_semantics":
        return LoweredVerificationResult(
            "lowered_evidence_unsupported", "ideal_construction", None, recomputed_bound,
            True, 0, memory_cap_bytes,
            f"ideal construction evidence is insufficient: {ideal.status}",
        )
    if lowered.optimization is not None:
        return LoweredVerificationResult(
            "lowered_evidence_unsupported",
            "external_equivalence_pair_required",
            None,
            recomputed_bound,
            True,
            0,
            memory_cap_bytes,
            "externally optimized streams require source-to-result verification",
        )
    expected_events, expected_phase, binding_error = _expected_emitted_stream(lowered)
    if binding_error is not None:
        return LoweredVerificationResult(
            "lowered_evidence_unsupported", "primitive_binding", None, recomputed_bound,
            True, 0, memory_cap_bytes, binding_error,
        )
    if expected_events != lowered.events:
        return LoweredVerificationResult(
            "verification_failure", "emitted_event_binding", None, recomputed_bound,
            True, 0, memory_cap_bytes,
            "emitted event stream does not match the independently reconstructed composition",
        )
    phase_distance = abs(
        cmath.exp(1j * expected_phase) - cmath.exp(1j * lowered.lowering_global_phase)
    )
    if phase_distance > 1e-10:
        return LoweredVerificationResult(
            "verification_failure", "emitted_event_binding", None, recomputed_bound,
            True, 0, memory_cap_bytes,
            "lowering global phase does not match the emitted rotation subsequences",
        )
    data_size = 1 << lowered.candidate.program.qubit_count
    full_size = 1 << (
        lowered.allocated_qubits
        or lowered.candidate.program.qubit_count
        + lowered.candidate.workspace_qubits
    )
    matrix_bytes = full_size * data_size * np.dtype(np.complex128).itemsize
    allocation_estimate = 3 * matrix_bytes
    if allocation_estimate > memory_cap_bytes:
        return LoweredVerificationResult(
            "verified_lowered_compositional",
            "ideal_semantics_primitive_matrices_event_binding_and_error_budget",
            None,
            recomputed_bound,
            True,
            matrix_bytes,
            memory_cap_bytes,
            "dense isometry skipped; independent compositional obligations were verified",
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


def verify_optimized_lowered_circuit(
    source: LoweredCircuit,
    result: LoweredCircuit,
    total_error: float,
    *,
    memory_cap_bytes: int = 32 * 1024 * 1024,
) -> LoweredVerificationResult:
    """Verify an exact external rewrite against its already-bound source stream."""
    source_verification = verify_lowered_circuit(
        source, total_error, memory_cap_bytes=memory_cap_bytes
    )
    if not source_verification.status.startswith("verified_lowered_"):
        return LoweredVerificationResult(
            "lowered_evidence_unsupported",
            "external_source",
            None,
            source.error_bound,
            True,
            0,
            memory_cap_bytes,
            f"external rewrite source is not verified: {source_verification.status}",
        )
    event_error = _validate_events(result)
    if event_error:
        return LoweredVerificationResult(
            "verification_failure", "validation", None, result.error_bound,
            False, 0, memory_cap_bytes, event_error
        )
    if result.candidate != source.candidate:
        return LoweredVerificationResult(
            "verification_failure", "external_boundary", None, result.error_bound,
            True, 0, memory_cap_bytes, "external rewrite changed the symbolic target"
        )
    if result.error_bound != source.error_bound or result.error_metric != source.error_metric:
        return LoweredVerificationResult(
            "verification_failure", "external_error_contract", None, result.error_bound,
            True, 0, memory_cap_bytes, "exact rewrite changed the synthesis-error contract"
        )
    if result.optimization is None:
        return LoweredVerificationResult(
            "verification_failure", "external_provenance", None, result.error_bound,
            True, 0, memory_cap_bytes, "external rewrite lacks backend provenance"
        )
    try:
        from ..adapters._pyzx_circuit import equivalence_phase, events_to_circuit

        qubits = source.candidate.program.qubit_count + source.candidate.workspace_qubits
        source_circuit = events_to_circuit(source.events, qubits)
        result_circuit = events_to_circuit(result.events, qubits)
        phase = equivalence_phase(source_circuit, result_circuit)
    except Exception as exc:
        return LoweredVerificationResult(
            "verification_failure", "external_equivalence", None, result.error_bound,
            True, 0, memory_cap_bytes, str(exc)
        )
    correction = result.lowering_global_phase - source.lowering_global_phase
    if abs(cmath.exp(1j * correction) - cmath.exp(-1j * phase)) > 1e-9:
        return LoweredVerificationResult(
            "verification_failure", "external_global_phase", None, result.error_bound,
            True, 0, memory_cap_bytes, "external global-phase correction is inconsistent"
        )
    data_size = 1 << result.candidate.program.qubit_count
    full_size = 1 << (
        result.allocated_qubits
        or result.candidate.program.qubit_count + result.candidate.workspace_qubits
    )
    matrix_bytes = full_size * data_size * np.dtype(np.complex128).itemsize
    if 3 * matrix_bytes <= memory_cap_bytes:
        error = _dense_isometry_error(result)
        if not math.isfinite(error) or error > total_error * (1 + 1e-7) + 1e-10:
            return LoweredVerificationResult(
                "verification_failure", "clean_input_isometry_spectral_norm", error,
                result.error_bound, True, matrix_bytes, memory_cap_bytes,
                "optimized clean-input isometry differs from the target",
            )
        return LoweredVerificationResult(
            "verified_lowered_external_dense",
            "external_equivalence_and_clean_input_isometry_spectral_norm",
            error,
            result.error_bound,
            True,
            matrix_bytes,
            memory_cap_bytes,
            "external rewrite equivalence and clean-input isometry verified",
        )
    return LoweredVerificationResult(
        "verified_lowered_external_compositional",
        "source_binding_external_equivalence_and_error_budget",
        None,
        result.error_bound,
        True,
        matrix_bytes,
        memory_cap_bytes,
        "external rewrite composed with verified source and synthesis error bound",
    )
