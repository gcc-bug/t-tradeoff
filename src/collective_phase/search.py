from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Protocol

from .adapters import AdapterResult
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
        }


@dataclass(frozen=True)
class _Proposal:
    source: SearchState
    action: ActionSpec
    priority: float
    reason: str
    provisional: bool


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
        0.0 if bound is None or bound == 0 else min(value / bound, 2.0)
        for value, bound in zip(values, bounds, strict=True)
    )


def _adaptive_priority(
    state: SearchState,
    action: ActionSpec,
    objective: FinalObjective,
    limits: SelectionLimits,
    incumbent: SearchState,
) -> tuple[float, str]:
    schedule = schedule_events(state.lowered.events)
    critical_fraction = (
        len(schedule.critical_t_events) / schedule.t_count if schedule.t_count else 0.0
    )
    toffoli_count = sum(
        operation.kind == "toffoli"
        for operation in state.lowered.candidate.operations
    )
    algebraic_opportunity = toffoli_count / (toffoli_count + 4)
    weights = _objective_weights(objective)
    pressure = _constraint_pressure(incumbent.resources, limits)
    demand = tuple(
        weight + constraint
        for weight, constraint in zip(weights, pressure, strict=True)
    )
    evidence = (
        action.orientation[0] * (1.0 + algebraic_opportunity),
        action.orientation[1] * (0.5 + critical_fraction),
        action.orientation[2],
    )
    priority = sum(
        need * support for need, support in zip(demand, evidence, strict=True)
    )
    if action.orientation[1] >= action.orientation[0]:
        reason = (
            f"{len(schedule.critical_t_events)}/{schedule.t_count} T gates are "
            "on a critical dependency path; prioritize depth resynthesis"
        )
    else:
        slack_events = sum(value > 0 for value in schedule.event_slack)
        reason = (
            f"count has weight/pressure {demand[0]:.3f} and "
            f"{slack_events} scheduled events have T-slack; {toffoli_count} logical "
            "Toffolis expose a joint exact-simplification opportunity"
        )
    return priority, reason


def _static_priority(policy: str, action: ActionSpec) -> tuple[float, str]:
    weights = {
        "static_t": (1.0, 0.0, 0.0),
        "static_depth": (0.0, 1.0, 0.0),
        "static_ancilla": (0.0, 0.0, 1.0),
        "static_t_lookahead": (1.0, 0.0, 0.0),
        "static_balanced": (1 / 3, 1 / 3, 1 / 3),
        "static_count_depth": (0.5, 0.5, 0.0),
        "static_count_ancilla": (0.5, 0.0, 0.5),
    }.get(policy, (1.0, 0.0, 0.0))
    return (
        sum(
            weight * support
            for weight, support in zip(weights, action.orientation, strict=True)
        ),
        f"fixed {policy.removeprefix('static_')} action priority",
    )


def _proposal_order(
    policy: str,
    sources: list[SearchState],
    actions: list[ActionSpec],
    objective: FinalObjective,
    limits: SelectionLimits,
    initial: SearchState,
    incumbent: SearchState,
    lookahead: bool,
) -> list[_Proposal]:
    proposals: list[_Proposal] = []
    for source in sources:
        if source is not initial and not lookahead:
            continue
        if limits.violation(source.resources) is not None:
            continue
        for action in actions:
            if policy.startswith("adaptive"):
                priority, reason = _adaptive_priority(
                    source, action, objective, limits, incumbent
                )
            elif policy == "fixed_order":
                priority = float(len(actions) - actions.index(action))
                reason = "predeclared construction/action order"
            else:
                priority, reason = _static_priority(policy, action)
            proposals.append(
                _Proposal(
                    source,
                    action,
                    priority,
                    reason,
                    source is not initial,
                )
            )
    return sorted(
        proposals,
        key=lambda item: (
            -item.priority,
            item.source.label,
            item.action.name,
        ),
    )


def _better(first: SearchState, second: SearchState, objective: FinalObjective) -> bool:
    return objective.rank(first.resources, first.label) < objective.rank(
        second.resources, second.label
    )


def default_actions(pyzx: Optimizer, feynman: Optimizer | None = None) -> list[ActionSpec]:
    actions = [
        ActionSpec("pyzx:zx_extract", "pyzx", "zx_extract", (1.0, 0.7, 0.1), pyzx),
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
    return actions


def run_policy(
    seeds: list[SearchState],
    actions: list[ActionSpec],
    objective: FinalObjective,
    limits: SelectionLimits,
    *,
    policy: str,
    max_backend_calls: int = 4,
    max_backend_seconds: float = 30.0,
) -> SearchResult:
    if max_backend_calls < 0 or max_backend_seconds <= 0:
        raise ValueError("search budgets must be non-negative calls and positive time")
    objective.validate_limits(limits)
    initial = next(
        (state for state in seeds if state.lowered.candidate.method == "independent"),
        None,
    )
    feasible_seeds = [
        state for state in seeds if limits.violation(state.resources) is None
    ]
    if initial is None or not feasible_seeds:
        return SearchResult(
            policy, "infeasible", objective, limits, initial, None, list(seeds),
            _pareto_labels(seeds), [], len(seeds), 0, 0.0, {"no_feasible_seed": 1}
        )
    best = min(
        feasible_seeds,
        key=lambda state: objective.rank(state.resources, state.label),
    )
    archive = list(seeds)
    rejections: Counter[str] = Counter()
    backend_calls = 0
    backend_seconds = 0.0
    evaluated_results: list[tuple[_Proposal, SearchState]] = []
    lookahead = policy in {"adaptive_lookahead", "static_t_lookahead", "fixed_order"}
    proposals = _proposal_order(
        policy, seeds, actions, objective, limits, initial, best, lookahead
    )
    for proposal in proposals:
        if backend_calls >= max_backend_calls:
            rejections["call_budget"] += 1
            break
        if backend_seconds >= max_backend_seconds:
            rejections["time_budget"] += 1
            break
        result = proposal.action.optimizer.optimize(
            proposal.source.lowered, proposal.action.action
        )
        backend_calls += 1
        backend_seconds += result.backend_seconds
        if not result.verified or result.lowered is None:
            rejections["backend_failure"] += 1
            continue
        verification = verify_optimized_lowered_circuit(
            proposal.source.lowered, result.lowered,
            proposal.source.total_error,
        )
        if not verification.status.startswith("verified_lowered_"):
            rejections["verification_inconclusive"] += 1
            continue
        resources = estimate_resources(result.lowered)
        if limits.violation(resources) is not None:
            rejections["hard_limit"] += 1
            continue
        state = SearchState(
            label=f"{proposal.source.label}|{proposal.action.name}",
            lowered=result.lowered,
            resources=resources,
            verification=verification,
            objective_value=objective.value(resources),
            source_seed=proposal.source.source_seed,
            total_error=proposal.source.total_error,
            action=proposal.action.name,
        )
        archive.append(state)
        evaluated_results.append((proposal, state))

    improving = [
        value for value in evaluated_results if _better(value[1], best, objective)
    ]
    trace: list[DecisionTraceRow] = []
    if improving:
        proposal, endpoint = min(
            improving,
            key=lambda value: objective.rank(value[1].resources, value[1].label),
        )
        step = 1
        if proposal.provisional:
            trace.append(
                DecisionTraceRow(
                    step,
                    "whole_circuit",
                    f"construction:{proposal.source.source_seed}",
                    "construction seed exposes a supported exact backend opportunity",
                    proposal.priority,
                    initial.resources.t_count,
                    proposal.source.resources.t_count,
                    initial.resources.t_depth,
                    proposal.source.resources.t_depth,
                    initial.resources.peak_workspace,
                    proposal.source.resources.peak_workspace,
                    initial.objective_value,
                    proposal.source.objective_value,
                    len(seeds),
                    0.0,
                    provisional=True,
                )
            )
            step += 1
        trace.append(
            DecisionTraceRow(
                step,
                "whole_circuit",
                proposal.action.name,
                proposal.reason,
                proposal.priority,
                proposal.source.resources.t_count,
                endpoint.resources.t_count,
                proposal.source.resources.t_depth,
                endpoint.resources.t_depth,
                proposal.source.resources.peak_workspace,
                endpoint.resources.peak_workspace,
                proposal.source.objective_value,
                endpoint.objective_value,
                len(seeds) + backend_calls,
                backend_seconds,
            )
        )
        best = endpoint
    else:
        rejections["no_objective_improvement"] += len(evaluated_results)
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
        evaluations=len(seeds) + backend_calls,
        backend_calls=backend_calls,
        backend_seconds=backend_seconds,
        rejection_counts=dict(sorted(rejections.items())),
    )
