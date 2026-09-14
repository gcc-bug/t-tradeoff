from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import hashlib
import json
import time
from typing import Protocol

from .adapters import AdapterResult, PyZXAdapter
from .adapters.phase_ancilla import PhaseAncillaAdapter, phase_regions
from .baselines import (
    compile_hwp_adder_unitary_alternatives,
    compile_independent,
    compile_shared_parity,
)
from .baselines.common import CompilationConstraints
from .ir import PhaseProgram
from .lowering import LoweredCircuit, RotationSynthesizer
from .resources import ResourceRecord, estimate_resources, schedule_events
from .selection import (
    EvaluatedAlternative,
    FinalObjective,
    SelectionLimits,
    evaluate_alternatives,
)
from .verification import (
    LoweredVerificationResult,
    verify_optimized_lowered_circuit,
)


class Optimizer(Protocol):
    def optimize(self, lowered: LoweredCircuit, action: str) -> AdapterResult: ...


@dataclass(frozen=True)
class ActionSpec:
    name: str
    backend: str
    action: str
    orientation: tuple[float, float, float]
    optimizer: Optimizer = field(compare=False, repr=False)
    scratch_allowances: tuple[int, ...] = (0,)


@dataclass
class SearchState:
    label: str
    lowered: LoweredCircuit
    resources: ResourceRecord
    verification: LoweredVerificationResult
    objective_value: float
    source_seed: str
    total_error: float
    action: str = "construction_seed"
    parent_id: str | None = None
    depth: int = 0
    ancestry: tuple[LoweredCircuit, ...] = field(default=(), repr=False)

    @property
    def resource_tuple(self) -> tuple[int, int, int]:
        return (
            self.resources.t_count,
            self.resources.t_depth,
            self.resources.peak_workspace,
        )


@dataclass(frozen=True)
class DecisionTraceRow:
    step: int
    region: str
    action_backend: str
    reason: str
    local_priority: float
    t_before: int
    t_after: int
    d_before: int
    d_after: int
    a_before: int
    a_after: int
    j_before: float
    j_after: float
    evaluations: int
    backend_seconds: float
    provisional: bool = False
    parent_id: str = ""
    output_id: str | None = None
    allowance: int = 0
    priority_vector: tuple[float, float, float] = (0.0, 0.0, 0.0)
    status: str = "accepted"
    verification_status: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchResult:
    policy: str
    status: str
    objective: FinalObjective
    limits: SelectionLimits
    initial: SearchState | None
    best: SearchState | None
    archive: list[SearchState]
    pareto_labels: list[str]
    trace: list[DecisionTraceRow]
    evaluations: int
    backend_calls: int
    backend_seconds: float
    rejection_counts: dict[str, int]
    total_seconds: float = 0.0
    verification_seconds: float = 0.0
    root_seconds: float = 0.0

    def summary(self) -> dict:
        return {
            "policy": self.policy,
            "status": self.status,
            "objective": self.objective.to_dict(),
            "limits": self.limits.to_dict(),
            "initial": None if self.initial is None else self.initial.label,
            "selected": None if self.best is None else self.best.label,
            "resources": None if self.best is None else list(self.best.resource_tuple),
            "objective_value": (
                None if self.best is None else self.best.objective_value
            ),
            "pareto": self.pareto_labels,
            "trace": [row.to_dict() for row in self.trace],
            "evaluations": self.evaluations,
            "backend_calls": self.backend_calls,
            "backend_seconds": self.backend_seconds,
            "rejection_counts": self.rejection_counts,
            "total_seconds": self.total_seconds,
            "verification_seconds": self.verification_seconds,
            "root_seconds": self.root_seconds,
        }


@dataclass(frozen=True)
class _Proposal:
    source: SearchState
    action: ActionSpec
    priority: float
    reason: str
    provisional: bool
    region: tuple[int, int] | None = None
    allowance: int = 0
    priority_vector: tuple[float, float, float] = (0.0, 0.0, 0.0)


def construction_seeds(
    program: PhaseProgram,
    constraints: CompilationConstraints,
    total_error: float,
    synthesizer: RotationSynthesizer,
    objective: FinalObjective,
) -> list[SearchState]:
    candidates = [
        compile_independent(program, constraints),
        compile_shared_parity(program, constraints),
        *compile_hwp_adder_unitary_alternatives(program, constraints),
    ]
    evaluated = evaluate_alternatives(candidates, total_error, synthesizer)
    states: list[SearchState] = []
    for item in evaluated:
        if not item.eligible:
            continue
        assert item.lowered is not None
        assert item.resources is not None
        assert item.lowered_verification is not None
        label = f"{item.candidate.method}:{item.candidate.variant}"
        states.append(
            SearchState(
                label=label,
                lowered=item.lowered,
                resources=item.resources,
                verification=item.lowered_verification,
                objective_value=objective.value(item.resources),
                source_seed=label,
                total_error=total_error,
            )
        )
    return states


def _dominates(first: SearchState, second: SearchState) -> bool:
    return all(
        left <= right
        for left, right in zip(first.resource_tuple, second.resource_tuple, strict=True)
    ) and any(
        left < right
        for left, right in zip(first.resource_tuple, second.resource_tuple, strict=True)
    )


def _pareto_labels(states: list[SearchState]) -> list[str]:
    return sorted(
        state.label
        for state in states
        if not any(other is not state and _dominates(other, state) for other in states)
    )


def _objective_weights(objective: FinalObjective) -> tuple[float, float, float]:
    if objective.mode == "balance":
        total = sum(objective.weights)
        return tuple(value / total for value in objective.weights)
    return {
        "t_count": (1.0, 0.0, 0.0),
        "t_depth": (0.0, 1.0, 0.0),
        "ancilla": (0.0, 0.0, 1.0),
    }[objective.metric]


def _constraint_pressure(
    resources: ResourceRecord, limits: SelectionLimits
) -> tuple[float, float, float]:
    values = (resources.t_count, resources.t_depth, resources.peak_workspace)
    bounds = (limits.t_count, limits.t_depth, limits.ancilla)
    return tuple(
        0.0 if bound is None or bound == 0 else max(0.0, value / bound - 0.8)
        for value, bound in zip(values, bounds, strict=True)
    )


def _adaptive_priority(
    state: SearchState,
    action: ActionSpec,
    objective: FinalObjective,
    limits: SelectionLimits,
    allowance: int,
) -> tuple[float, str, tuple[float, float, float]]:
    schedule = schedule_events(state.lowered.events)
    critical_fraction = (
        len(schedule.critical_t_events) / schedule.t_count if schedule.t_count else 0.0
    )
    weights = _objective_weights(objective)
    pressure = _constraint_pressure(state.resources, limits)
    demand = tuple(
        weight + constraint
        for weight, constraint in zip(weights, pressure, strict=True)
    )
    evidence = (
        action.orientation[0],
        action.orientation[1] * (0.5 + critical_fraction),
        action.orientation[2] - allowance / objective.ancilla_reference,
    )
    priority = sum(
        need * support for need, support in zip(demand, evidence, strict=True)
    )
    if allowance:
        reason = (
            f"{len(schedule.critical_t_events)}/{schedule.t_count} T gates on "
            f"critical paths; {allowance} clean scratch wires requested "
            "for a supported CNOT/phase region; depth gain is unproven"
        )
    elif action.orientation[1] >= action.orientation[0]:
        reason = (
            f"{len(schedule.critical_t_events)}/{schedule.t_count} T gates are "
            "on a critical dependency path; prioritize depth resynthesis"
        )
    else:
        reason = (
            f"count priority {demand[0]:.3f}; "
            f"{sum(value > 0 for value in schedule.event_slack)} current events have T-slack"
        )
    return priority, reason, demand


def _static_priority(policy: str, action: ActionSpec, allowance: int) -> tuple[float, str, tuple[float, float, float]]:
    weights = {
        "static_t": (1.0, 0.0, 0.0),
        "static_depth": (0.0, 1.0, 0.0),
        "static_ancilla": (0.0, 0.0, 1.0),
        "static_balanced": (1 / 3, 1 / 3, 1 / 3),
    }.get(policy, (1.0, 0.0, 0.0))
    return (
        sum(
            weight * support
            for weight, support in zip(
                weights, (action.orientation[0], action.orientation[1],
                          action.orientation[2] - allowance), strict=True
            )
        ),
        f"fixed {policy.removeprefix('static_')} action priority",
        weights,
    )


def _proposal_order(
    policy: str,
    sources: list[SearchState],
    actions: list[ActionSpec],
    objective: FinalObjective,
    limits: SelectionLimits,
    attempted: set[tuple[str, str, tuple[int, int] | None, int]],
    roots: dict[str, SearchState],
    max_depth: int,
) -> list[_Proposal]:
    proposals: list[_Proposal] = []
    for source in sources:
        if source.depth >= max_depth or limits.violation(source.resources) is not None:
            continue
        for action in actions:
            if action.backend == "phase_ancilla" and source.action == action.name:
                continue
            if policy.startswith("fixed_"):
                names = (
                    ("pyzx:zx_extract", "phase_ancilla:parallel_phase")
                    if policy == "fixed_count_depth"
                    else ("phase_ancilla:parallel_phase", "pyzx:zx_extract")
                )
                if action.name != names[source.depth % len(names)]:
                    continue
            regions = phase_regions(source.lowered.events) if action.backend == "phase_ancilla" else [None]
            for region in regions:
                for allowance in action.scratch_allowances:
                    if (source.label, action.name, region, allowance) in attempted:
                        continue
                    if limits.ancilla is not None and source.resources.peak_workspace + allowance > limits.ancilla:
                        continue
                    if policy == "adaptive":
                        priority, reason, vector = _adaptive_priority(source, action, objective, limits, allowance)
                    elif policy == "frozen":
                        priority, reason, vector = _adaptive_priority(roots[source.source_seed], action, objective, limits, allowance)
                        reason = "frozen seed priority; " + reason
                    elif policy.startswith("fixed_"):
                        priority, reason, vector = float(max_depth - source.depth), "predeclared successive pass sequence", (0.0, 0.0, 0.0)
                    else:
                        priority, reason, vector = _static_priority(policy, action, allowance)
                    proposals.append(_Proposal(source, action, priority, reason, source.depth > 0, region, allowance, vector))
    return sorted(
        proposals,
        key=lambda item: (
            -item.priority,
            item.source.depth,
            item.source.label,
            item.action.name,
            item.allowance,
        ),
    )


def _better(first: SearchState, second: SearchState, objective: FinalObjective) -> bool:
    return objective.rank(first.resources, first.label) < objective.rank(
        second.resources, second.label
    )


def default_actions(pyzx: Optimizer, feynman: Optimizer | None = None) -> list[ActionSpec]:
    actions = [
        ActionSpec("pyzx:zx_extract", "pyzx", "zx_extract", (1.0, 0.7, 0.0), pyzx),
        ActionSpec("pyzx:todd", "pyzx", "todd", (1.0, 0.4, 0.0), pyzx),
    ]
    if feynman is not None:
        actions.extend(
            [
                ActionSpec("feynman:tpar", "feynman", "tpar", (0.4, 1.0, 0.0), feynman),
                ActionSpec(
                    "feynman:phasefold",
                    "feynman",
                    "phasefold",
                    (0.9, 0.2, 0.0),
                    feynman,
                ),
            ]
        )
    actions.append(
        ActionSpec(
            "phase_ancilla:parallel_phase", "phase_ancilla", "parallel_phase",
            (0.0, 1.0, 0.0), PhaseAncillaAdapter(), (1, 2, 4),
        )
    )
    return actions


def _state_key(state: SearchState) -> str:
    lowered = state.lowered
    encoded = json.dumps(
        (lowered.candidate.program.id, lowered.candidate.global_phase,
         lowered.lowering_global_phase, lowered.error_bound,
         lowered.allocated_qubits, [event.to_dict() for event in lowered.events]),
        sort_keys=True, separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def run_policy(
    seeds: list[SearchState],
    actions: list[ActionSpec],
    objective: FinalObjective,
    limits: SelectionLimits,
    *,
    policy: str,
    max_backend_calls: int = 12,
    max_backend_seconds: float = 60.0,
    max_depth: int = 3,
    pool_capacity: int = 4,
) -> SearchResult:
    if max_backend_calls < 0 or max_backend_seconds <= 0 or max_depth < 1 or pool_capacity < 1:
        raise ValueError("invalid search call, time, depth, or pool budget")
    started = time.monotonic()
    deadline = started + max_backend_seconds
    objective.validate_limits(limits)
    initial = next(
        (state for state in seeds if state.lowered.candidate.method == "independent"),
        None,
    )
    unique: dict[str, SearchState] = {}
    for seed in seeds:
        unique.setdefault(_state_key(seed), seed)
    roots = list(unique.values())
    feasible_seeds = [state for state in roots if limits.violation(state.resources) is None]
    if not feasible_seeds:
        return SearchResult(
            policy, "no_feasible_seed", objective, limits, initial, None, list(roots),
            [], [], len(roots), 0, 0.0, {"no_feasible_seed": 1},
            total_seconds=time.monotonic() - started,
        )
    best = min(
        feasible_seeds,
        key=lambda state: objective.rank(state.resources, state.label),
    )
    archive = list(feasible_seeds)
    rejections: Counter[str] = Counter()
    backend_calls = 0
    backend_seconds = 0.0
    verification_seconds = 0.0
    transformed: list[SearchState] = []
    seen = {_state_key(state) for state in roots}
    attempted: set[tuple[str, str, tuple[int, int] | None, int]] = set()
    root_index = {state.label: state for state in roots}
    trace: list[DecisionTraceRow] = []
    while backend_calls < max_backend_calls and time.monotonic() < deadline:
        proposals = _proposal_order(
            policy, [*feasible_seeds, *transformed], actions, objective, limits,
            attempted, root_index, max_depth,
        )
        if not proposals:
            break
        if backend_calls % 3 == 2:
            continuation = next((item for item in proposals if item.source.depth > 0), None)
            proposal = continuation or proposals[0]
        else:
            proposal = proposals[0]
        attempted.add((proposal.source.label, proposal.action.name, proposal.region, proposal.allowance))
        attempt_started = time.monotonic()
        remaining = deadline - attempt_started
        if proposal.region is not None:
            result = proposal.action.optimizer.optimize_region(
                proposal.source.lowered, proposal.region, proposal.allowance
            )
        elif proposal.action.backend == "feynman":
            result = proposal.action.optimizer.optimize(
                proposal.source.lowered, proposal.action.action,
                timeout_seconds=remaining,
            )
        elif isinstance(proposal.action.optimizer, PyZXAdapter):
            result = proposal.action.optimizer.optimize(
                proposal.source.lowered, proposal.action.action,
                timeout_seconds=remaining,
            )
        else:
            result = proposal.action.optimizer.optimize(
                proposal.source.lowered, proposal.action.action
            )
        backend_calls += 1
        backend_seconds += result.backend_seconds
        status = "accepted"
        verification_status = None
        state = None
        measured_resources = None
        if not result.verified or result.lowered is None:
            status = "timeout" if result.status == "timed_out" else "backend_failure"
        else:
            verify_started = time.monotonic()
            verification = verify_optimized_lowered_circuit(
                proposal.source.lowered, result.lowered, proposal.source.total_error,
                ancestry=proposal.source.ancestry,
                timeout_seconds=max(0.0, deadline - time.monotonic()),
            )
            verification_seconds += time.monotonic() - verify_started
            verification_status = verification.status
            if not verification.status.startswith("verified_lowered_"):
                status = "verification_inconclusive" if "unsupported" in verification.status else "verification_failure"
            else:
                resources = estimate_resources(result.lowered)
                measured_resources = resources
                if limits.violation(resources) is not None:
                    status = "hard_limit"
                else:
                    label = f"{proposal.source.label}|{proposal.action.name}"
                    if proposal.region is not None:
                        label += f":region_{proposal.region[0]}_{proposal.region[1]}"
                    if proposal.allowance:
                        label += f":scratch_{proposal.allowance}"
                    state = SearchState(
                        label=label, lowered=result.lowered, resources=resources,
                        verification=verification, objective_value=objective.value(resources),
                        source_seed=proposal.source.source_seed,
                        total_error=proposal.source.total_error, action=proposal.action.name,
                        parent_id=proposal.source.label, depth=proposal.source.depth + 1,
                        ancestry=(*proposal.source.ancestry, proposal.source.lowered),
                    )
                    identity = _state_key(state)
                    if identity in seen:
                        if policy.startswith("fixed_") and state.depth == 1 and identity == _state_key(proposal.source):
                            status = "unchanged"
                            transformed = sorted(
                                [*transformed, state],
                                key=lambda item: objective.rank(item.resources, item.label),
                            )[:pool_capacity]
                        else:
                            status = "no_change_or_cycle"
                            state = None
                    else:
                        seen.add(identity)
                        archive.append(state)
                        if _better(state, best, objective):
                            best = state
                        transformed = sorted(
                            [*transformed, state],
                            key=lambda item: (item is not best, objective.rank(item.resources, item.label)),
                        )[:pool_capacity]
        if status not in {"accepted", "unchanged"}:
            rejections[status] += 1
        after = measured_resources if measured_resources is not None else proposal.source.resources
        trace.append(DecisionTraceRow(
            backend_calls,
            f"{proposal.region[0]}:{proposal.region[1]}" if proposal.region else "whole_circuit",
            proposal.action.name, proposal.reason if status == "accepted" else f"{proposal.reason}; {result.reason or status}",
            proposal.priority, proposal.source.resources.t_count, after.t_count,
            proposal.source.resources.t_depth, after.t_depth,
            proposal.source.resources.peak_workspace, after.peak_workspace,
            proposal.source.objective_value, objective.value(after),
            len(roots) + backend_calls, time.monotonic() - attempt_started,
            provisional=state is not None and state is not best,
            parent_id=proposal.source.label, output_id=state.label if state else None,
            allowance=proposal.allowance, priority_vector=proposal.priority_vector,
            status=status, verification_status=verification_status,
        ))
    if backend_calls >= max_backend_calls:
        rejections["call_budget"] += 1
    elif time.monotonic() >= deadline:
        rejections["time_budget"] += 1
    return SearchResult(
        policy=policy,
        status="success",
        objective=objective,
        limits=limits,
        initial=initial,
        best=best,
        archive=archive,
        pareto_labels=_pareto_labels(archive),
        trace=trace,
        evaluations=len(roots) + backend_calls,
        backend_calls=backend_calls,
        backend_seconds=backend_seconds,
        rejection_counts=dict(sorted(rejections.items())),
        total_seconds=time.monotonic() - started,
        verification_seconds=verification_seconds,
    )
