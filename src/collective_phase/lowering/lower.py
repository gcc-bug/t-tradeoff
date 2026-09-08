from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from ..circuit import Candidate, Operation
from ..ir import ScaledAngle
from .synthesis import RotationSynthesis, RotationSynthesizer


@dataclass(frozen=True)
class GateEvent:
    kind: str
    qubits: tuple[int, ...]


@dataclass(frozen=True)
class MacroEvent:
    kind: str
    qubits: tuple[int, ...]
    t_count: int
    t_depth: int
    measurement_count: int = 0
    adaptive_rounds: int = 0
    clifford_count: int | None = None
    source: str = ""


@dataclass
class LoweredCircuit:
    candidate: Candidate
    events: list[GateEvent | MacroEvent] = field(default_factory=list)
    preparation_rotations: list[RotationSynthesis] = field(default_factory=list)
    application_rotations: list[RotationSynthesis] = field(default_factory=list)
    lowering_global_phase: float = 0.0
    error_bound: float = 0.0
    error_metric: str = "operator_norm_telescoping"


def _toffoli_events(qubits: tuple[int, ...]) -> list[GateEvent]:
    first, second, target = qubits
    # Standard exact 7-T, ancilla-free Toffoli decomposition.
    sequence = [
        ("h", (target,)),
        ("cx", (second, target)),
        ("tdg", (target,)),
        ("cx", (first, target)),
        ("t", (target,)),
        ("cx", (second, target)),
        ("tdg", (target,)),
        ("cx", (first, target)),
        ("t", (second,)),
        ("t", (target,)),
        ("h", (target,)),
        ("cx", (first, second)),
        ("t", (first,)),
        ("tdg", (second,)),
        ("cx", (first, second)),
    ]
    return [GateEvent(kind, wires) for kind, wires in sequence]


def _emit_rotation(
    lowered: LoweredCircuit,
    synthesis: RotationSynthesis,
    target: int,
) -> None:
    for gate in synthesis.gates:
        if gate == "w":
            lowered.lowering_global_phase += math.pi / 4
            continue
        lowered.events.append(GateEvent(gate, (target,)))
    if not synthesis.exact:
        # P(alpha) = exp(i alpha/2) Rz(alpha). The backend's circuit phase is
        # stored separately because the simple gate stream omits it.
        lowered.lowering_global_phase += synthesis.circuit_global_phase


def _angle_requests(candidate: Candidate) -> tuple[list[ScaledAngle], list[ScaledAngle]]:
    application: list[ScaledAngle] = []
    for operation in candidate.operations:
        if operation.kind in {"phase", "phase_gradient"}:
            application.append(
                candidate.program.angle_map[operation.angle_id].scaled(operation.multiplier)
            )
    preparation: list[ScaledAngle] = []
    for state in candidate.required_resource_states:
        binding = candidate.program.angle_map[state["angle_id"]]
        preparation.extend(binding.scaled(int(value)) for value in state["multipliers"])
    return application, preparation


def _allocate_tolerances(
    candidate: Candidate,
    application: list[ScaledAngle],
    preparation: list[ScaledAngle],
    total_error: float,
) -> tuple[float, float]:
    app_generic = sum(not angle.is_exact_clifford_t for angle in application)
    prep_generic = sum(not angle.is_exact_clifford_t for angle in preparation)
    reuse = int(candidate.parameters.get("reuse_count", 1))
    if prep_generic and app_generic:
        return total_error / (2 * app_generic * reuse), total_error / (2 * prep_generic)
    if app_generic:
        return total_error / (app_generic * reuse), total_error
    if prep_generic:
        return total_error, total_error / prep_generic
    return total_error, total_error


def lower_candidate(
    candidate: Candidate,
    total_error: float,
    synthesizer: RotationSynthesizer,
) -> LoweredCircuit:
    if candidate.status != "success":
        raise ValueError("cannot lower an unsuccessful candidate")
    lowered = LoweredCircuit(candidate=candidate)
    application_angles, preparation_angles = _angle_requests(candidate)
    app_tolerance, prep_tolerance = _allocate_tolerances(
        candidate, application_angles, preparation_angles, total_error
    )
    app_results = [synthesizer.synthesize(angle, app_tolerance) for angle in application_angles]
    prep_results = [synthesizer.synthesize(angle, prep_tolerance) for angle in preparation_angles]
    lowered.application_rotations = app_results
    lowered.preparation_rotations = prep_results
    app_iterator = iter(app_results)

    for operation in candidate.operations:
        kind = operation.kind
        if kind in {"x", "cx"}:
            lowered.events.append(GateEvent(kind, operation.qubits))
        elif kind in {"toffoli", "and_compute", "and_uncompute"}:
            if candidate.model_profile == "unitary_clifford_t" or kind == "toffoli":
                lowered.events.extend(_toffoli_events(operation.qubits))
            elif kind == "and_compute":
                lowered.events.append(
                    MacroEvent(
                        "temporary_and_compute",
                        operation.qubits,
                        t_count=4,
                        t_depth=1,
                        clifford_count=None,
                        source="Gidney, arXiv:1709.06648v3",
                    )
                )
            else:
                lowered.events.append(
                    MacroEvent(
                        "temporary_and_uncompute",
                        operation.qubits,
                        t_count=0,
                        t_depth=0,
                        measurement_count=1,
                        adaptive_rounds=1,
                        clifford_count=None,
                        source="Gidney, arXiv:1709.06648v3",
                    )
                )
        elif kind == "phase":
            synthesis = next(app_iterator)
            _emit_rotation(lowered, synthesis, operation.qubits[0])
            if not synthesis.exact:
                angle = candidate.program.angle_map[operation.angle_id].scaled(operation.multiplier)
                lowered.lowering_global_phase += angle.radians / 2
        elif kind in {"hwp_compute", "hwp_uncompute"}:
            size = int(operation.payload["batch_size"])
            adders = size - size.bit_count()
            layers = max(1, math.ceil(math.log2(size)))
            if candidate.model_profile == "measurement_assisted_clifford_t":
                is_compute = kind == "hwp_compute"
                lowered.events.append(
                    MacroEvent(
                        kind,
                        operation.qubits,
                        t_count=4 * adders if is_compute else 0,
                        t_depth=layers if is_compute else 0,
                        measurement_count=0 if is_compute else adders,
                        adaptive_rounds=0 if is_compute else layers,
                        clifford_count=None,
                        source="Kivlichan et al., arXiv:1902.10673v4 Appendix A",
                    )
                )
            else:
                lowered.events.append(
                    MacroEvent(
                        kind,
                        operation.qubits,
                        t_count=7 * adders,
                        t_depth=3 * layers,
                        clifford_count=None,
                        source="7-T unitary Toffoli substitution; HWP macro not emitted",
                    )
                )
        elif kind == "phase_gradient":
            gradient_toffolis = int(operation.payload["gradient_toffolis"])
            lowered.events.append(
                MacroEvent(
                    "phase_gradient_arithmetic",
                    operation.qubits,
                    t_count=7 * gradient_toffolis,
                    t_depth=3 * gradient_toffolis,
                    clifford_count=None,
                    source="Kan-Symons arXiv:2411.02160v2; unitary 7-T Toffolis",
                )
            )
            synthesis = next(app_iterator)
            _emit_rotation(lowered, synthesis, operation.qubits[0])
            if not synthesis.exact:
                angle = candidate.program.angle_map[operation.angle_id].scaled(operation.multiplier)
                lowered.lowering_global_phase += angle.radians / 2
        else:
            raise ValueError(f"unsupported lowering operation {kind!r}")

    try:
        next(app_iterator)
    except StopIteration:
        pass
    else:
        raise AssertionError("not all synthesized application rotations were consumed")

    reuse = int(candidate.parameters.get("reuse_count", 1))
    prep_error = sum(result.actual_operator_error for result in prep_results)
    app_error = sum(result.actual_operator_error for result in app_results)
    lowered.error_bound = prep_error + reuse * app_error
    if lowered.error_bound > total_error * (1 + 1e-7):
        raise RuntimeError("composed synthesis error exceeds configured total budget")
    return lowered
