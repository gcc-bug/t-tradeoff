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

    def to_dict(self) -> dict[str, Any]:
        return {"event_type": "gate", "kind": self.kind, "qubits": list(self.qubits)}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GateEvent":
        if value.get("event_type", "gate") != "gate":
            raise ValueError("not a gate event")
        return cls(value["kind"], tuple(int(qubit) for qubit in value["qubits"]))


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": "macro",
            "kind": self.kind,
            "qubits": list(self.qubits),
            "t_count": self.t_count,
            "t_depth": self.t_depth,
            "measurement_count": self.measurement_count,
            "adaptive_rounds": self.adaptive_rounds,
            "clifford_count": self.clifford_count,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MacroEvent":
        if value.get("event_type", "macro") != "macro":
            raise ValueError("not a macro event")
        return cls(
            kind=value["kind"],
            qubits=tuple(int(qubit) for qubit in value["qubits"]),
            t_count=int(value["t_count"]),
            t_depth=int(value["t_depth"]),
            measurement_count=int(value.get("measurement_count", 0)),
            adaptive_rounds=int(value.get("adaptive_rounds", 0)),
            clifford_count=(
                None
                if value.get("clifford_count") is None
                else int(value["clifford_count"])
            ),
            source=value.get("source", ""),
        )


@dataclass
class LoweredCircuit:
    candidate: Candidate
    events: list[GateEvent | MacroEvent] = field(default_factory=list)
    preparation_rotations: list[RotationSynthesis] = field(default_factory=list)
    application_rotations: list[RotationSynthesis] = field(default_factory=list)
    lowering_global_phase: float = 0.0
    error_bound: float = 0.0
    error_metric: str = "operator_norm_telescoping"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "events": [event.to_dict() for event in self.events],
            "rotations": {
                "application": [value.to_dict() for value in self.application_rotations],
                "preparation": [value.to_dict() for value in self.preparation_rotations],
            },
            "lowering_global_phase": self.lowering_global_phase,
            "total_global_phase": (
                self.candidate.global_phase + self.lowering_global_phase
            ),
            "error_bound": self.error_bound,
            "error_metric": self.error_metric,
        }

    @classmethod
    def from_dict(
        cls, value: dict[str, Any], candidate: Candidate
    ) -> "LoweredCircuit":
        events: list[GateEvent | MacroEvent] = []
        for event in value.get("events", []):
            event_type = event.get("event_type")
            if event_type == "macro" or (
                event_type is None and "t_count" in event
            ):
                events.append(MacroEvent.from_dict(event))
            else:
                events.append(GateEvent.from_dict(event))
        rotations = value.get("rotations", {})
        return cls(
            candidate=candidate,
            events=events,
            preparation_rotations=[
                RotationSynthesis.from_dict(item)
                for item in rotations.get("preparation", [])
            ],
            application_rotations=[
                RotationSynthesis.from_dict(item)
                for item in rotations.get("application", [])
            ],
            lowering_global_phase=float(value.get("lowering_global_phase", 0.0)),
            error_bound=float(value.get("error_bound", 0.0)),
            error_metric=value.get("error_metric", "operator_norm_telescoping"),
        )


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
    application_angles, preparation_angles = _angle_requests(candidate)
    app_tolerance, prep_tolerance = _allocate_tolerances(
        candidate, application_angles, preparation_angles, total_error
    )
    app_results = [synthesizer.synthesize(angle, app_tolerance) for angle in application_angles]
    prep_results = [synthesizer.synthesize(angle, prep_tolerance) for angle in preparation_angles]
    return lower_candidate_with_rotations(
        candidate, total_error, app_results, prep_results
    )


def lower_candidate_with_rotations(
    candidate: Candidate,
    total_error: float,
    application_rotations: list[RotationSynthesis],
    preparation_rotations: list[RotationSynthesis],
) -> LoweredCircuit:
    """Rebuild a gate stream from persisted rotation-synthesis evidence."""
    if candidate.status != "success":
        raise ValueError("cannot lower an unsuccessful candidate")
    application_angles, preparation_angles = _angle_requests(candidate)
    if len(application_angles) != len(application_rotations):
        raise ValueError("application rotation count does not match candidate")
    if len(preparation_angles) != len(preparation_rotations):
        raise ValueError("preparation rotation count does not match candidate")
    for angle, result in zip(application_angles, application_rotations, strict=True):
        if result.angle_key != angle.cache_key:
            raise ValueError("application rotation identity does not match candidate")
    for angle, result in zip(preparation_angles, preparation_rotations, strict=True):
        if result.angle_key != angle.cache_key:
            raise ValueError("preparation rotation identity does not match candidate")
    lowered = LoweredCircuit(
        candidate=candidate,
        application_rotations=list(application_rotations),
        preparation_rotations=list(preparation_rotations),
    )
    app_iterator = iter(application_rotations)

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
    prep_error = sum(result.actual_operator_error for result in preparation_rotations)
    app_error = sum(result.actual_operator_error for result in application_rotations)
    lowered.error_bound = prep_error + reuse * app_error
    if lowered.error_bound > total_error * (1 + 1e-7):
        raise RuntimeError("composed synthesis error exceeds configured total budget")
    return lowered
