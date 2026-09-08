from __future__ import annotations

from dataclasses import asdict, dataclass

from .lowering.lower import GateEvent, LoweredCircuit, MacroEvent


@dataclass(frozen=True)
class ResourceRecord:
    t_count: int
    t_depth: int
    peak_workspace: int
    total_qubits: int
    clifford_count: int | None
    measurement_count: int
    adaptive_rounds: int
    preparation_t: int
    application_t: int
    preparation_depth: int
    application_depth: int
    reuse_count: int
    amortized_t: float
    accounting_status: str

    def to_dict(self) -> dict:
        return asdict(self)


def _schedule(events: list[GateEvent | MacroEvent]) -> tuple[int, int]:
    levels: dict[int, int] = {}
    t_count = 0
    for event in events:
        current = max((levels.get(qubit, 0) for qubit in event.qubits), default=0)
        if isinstance(event, GateEvent):
            increment = 1 if event.kind in {"t", "tdg"} else 0
            t_count += increment
        else:
            increment = event.t_depth
            t_count += event.t_count
        updated = current + increment
        for qubit in event.qubits:
            levels[qubit] = updated
    return t_count, max(levels.values(), default=0)


def estimate_resources(lowered: LoweredCircuit) -> ResourceRecord:
    application_t, application_depth = _schedule(lowered.events)
    prep_t = sum(rotation.t_count for rotation in lowered.preparation_rotations)
    # Catalyst qubits are prepared independently, so their synthesis depths are
    # the maximum single-qubit T count, not their sum.
    prep_depth = max((rotation.t_count for rotation in lowered.preparation_rotations), default=0)
    reuse = int(lowered.candidate.parameters.get("reuse_count", 1))
    t_count = prep_t + reuse * application_t
    t_depth = prep_depth + reuse * application_depth
    emitted_cliffords = sum(
        isinstance(event, GateEvent) and event.kind not in {"t", "tdg", "w"}
        for event in lowered.events
    ) + sum(rotation.clifford_count for rotation in lowered.preparation_rotations)
    macro_cliffords_known = all(
        not isinstance(event, MacroEvent) or event.clifford_count is not None
        for event in lowered.events
    )
    if macro_cliffords_known:
        clifford_count: int | None = emitted_cliffords + sum(
            event.clifford_count or 0
            for event in lowered.events
            if isinstance(event, MacroEvent)
        )
    else:
        clifford_count = None
    measurement_count = reuse * sum(
        event.measurement_count
        for event in lowered.events
        if isinstance(event, MacroEvent)
    )
    adaptive_rounds = reuse * sum(
        event.adaptive_rounds
        for event in lowered.events
        if isinstance(event, MacroEvent)
    )
    return ResourceRecord(
        t_count=t_count,
        t_depth=t_depth,
        peak_workspace=lowered.candidate.workspace_qubits,
        total_qubits=(
            lowered.candidate.program.qubit_count + lowered.candidate.workspace_qubits
        ),
        clifford_count=clifford_count,
        measurement_count=measurement_count,
        adaptive_rounds=adaptive_rounds,
        preparation_t=prep_t,
        application_t=application_t,
        preparation_depth=prep_depth,
        application_depth=application_depth,
        reuse_count=reuse,
        amortized_t=t_count / reuse,
        accounting_status=lowered.candidate.accounting_status,
    )

