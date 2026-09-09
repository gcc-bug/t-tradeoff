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


@dataclass(frozen=True)
class TradeoffRecord:
    application_rotations: int
    generic_application_rotations: int
    exact_application_rotations: int
    preparation_rotations: int
    generic_preparation_rotations: int
    exact_preparation_rotations: int
    logical_toffoli_count: int
    logical_cx_count: int
    logical_x_count: int
    arithmetic_t: int | None
    rotation_t: int | None

    def to_dict(self) -> dict:
        return asdict(self)


def characterize_tradeoff(lowered: LoweredCircuit) -> TradeoffRecord:
    application = lowered.application_rotations
    preparation = lowered.preparation_rotations
    operations = lowered.candidate.operations
    reuse = int(lowered.candidate.parameters.get("reuse_count", 1))
    application_rotation_t = sum(item.t_count for item in application)
    preparation_rotation_t = sum(item.t_count for item in preparation)
    emitted_application_t = sum(
        (1 if event.kind in {"t", "tdg"} else 0)
        if isinstance(event, GateEvent)
        else event.t_count
        for event in lowered.events
    )
    if lowered.optimization is None:
        rotation_t: int | None = preparation_rotation_t + reuse * application_rotation_t
        arithmetic_t: int | None = reuse * (
            emitted_application_t - application_rotation_t
        )
    else:
        rotation_t = None
        arithmetic_t = None
    return TradeoffRecord(
        application_rotations=len(application),
        generic_application_rotations=sum(not item.exact for item in application),
        exact_application_rotations=sum(item.exact for item in application),
        preparation_rotations=len(preparation),
        generic_preparation_rotations=sum(not item.exact for item in preparation),
        exact_preparation_rotations=sum(item.exact for item in preparation),
        logical_toffoli_count=sum(item.kind == "toffoli" for item in operations),
        logical_cx_count=sum(item.kind == "cx" for item in operations),
        logical_x_count=sum(item.kind == "x" for item in operations),
        arithmetic_t=arithmetic_t,
        rotation_t=rotation_t,
    )


@dataclass(frozen=True)
class ScheduleRecord:
    t_count: int
    t_depth: int
    event_levels: tuple[int, ...]
    event_slack: tuple[int, ...]
    critical_t_events: tuple[int, ...]


def schedule_events(events: list[GateEvent | MacroEvent]) -> ScheduleRecord:
    levels: dict[int, int] = {}
    last_event: dict[int, int] = {}
    dependencies: list[set[int]] = []
    successors: list[set[int]] = [set() for _ in events]
    starts: list[int] = []
    weights: list[int] = []
    t_count = 0
    for index, event in enumerate(events):
        event_dependencies = {
            last_event[qubit] for qubit in event.qubits if qubit in last_event
        }
        dependencies.append(event_dependencies)
        for dependency in event_dependencies:
            successors[dependency].add(index)
        current = max((levels.get(qubit, 0) for qubit in event.qubits), default=0)
        if isinstance(event, GateEvent):
            increment = 1 if event.kind in {"t", "tdg"} else 0
            t_count += increment
        else:
            increment = event.t_depth
            t_count += event.t_count
        starts.append(current)
        weights.append(increment)
        updated = current + increment
        for qubit in event.qubits:
            levels[qubit] = updated
            last_event[qubit] = index

    t_depth = max(levels.values(), default=0)
    tails = [0] * len(events)
    for index in reversed(range(len(events))):
        tails[index] = weights[index] + max(
            (tails[value] for value in successors[index]), default=0
        )
    slack = tuple(
        t_depth - (starts[index] + tails[index]) for index in range(len(events))
    )
    critical = tuple(
        index
        for index, weight in enumerate(weights)
        if weight and slack[index] == 0
    )
    return ScheduleRecord(
        t_count=t_count,
        t_depth=t_depth,
        event_levels=tuple(starts),
        event_slack=slack,
        critical_t_events=critical,
    )


def _schedule(events: list[GateEvent | MacroEvent]) -> tuple[int, int]:
    schedule = schedule_events(events)
    return schedule.t_count, schedule.t_depth


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
    declared_qubits = (
        lowered.candidate.program.qubit_count
        + lowered.candidate.workspace_qubits
    )
    allocated_qubits = lowered.allocated_qubits or declared_qubits
    if not lowered.candidate.program.qubit_count <= allocated_qubits <= declared_qubits:
        raise ValueError("allocated qubits must include data and fit the declared circuit")
    return ResourceRecord(
        t_count=t_count,
        t_depth=t_depth,
        peak_workspace=allocated_qubits - lowered.candidate.program.qubit_count,
        total_qubits=allocated_qubits,
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
