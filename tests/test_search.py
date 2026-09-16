from dataclasses import replace

from collective_phase.adapters import AdapterResult, PhaseAncillaAdapter, PyZXAdapter
from collective_phase.adapters.phase_ancilla import phase_regions
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import GateEvent, RotationSynthesizer
from collective_phase.search import (
    ActionSpec,
    SearchState,
    _adaptive_priority,
    _preference_vector,
    _proposal_order,
    _state_key,
    construction_seeds,
    default_actions,
    run_policy,
)
from collective_phase.resources import estimate_resources, schedule_events
from collective_phase.selection import FinalObjective, SelectionLimits


def test_matched_policies_can_optimize_hwp_and_fixed_order_is_successive(tmp_path):
    program = make_program(
        "four", 4, [1, 2, 4, 8], AngleBinding("theta", "0.173")
    )
    objective = FinalObjective.from_value(
        {
            "mode": "balance",
            "weights": {"t_count": 0.9, "t_depth": 0.05, "ancilla": 0.05},
            "references": {"t_count": 200, "t_depth": 200, "ancilla": 8},
        }
    )
    limits = SelectionLimits(ancilla=8)
    seeds = construction_seeds(
        program,
        CompilationConstraints(8, "unitary_clifford_t", hwp_search_cap=4),
        1e-4,
        RotationSynthesizer(tmp_path / "rotations.json"),
        objective,
    )
    actions = default_actions(PyZXAdapter(seed=0))
    common = [state for state in seeds if state.lowered.candidate.method in {"independent", "hwp_adder_unitary"}]
    common = [state for state in common if state.lowered.candidate.method == "independent" or state.label.endswith("cap_4")]
    assert len(common) == 2
    for policy in ("adaptive", "static_t", "frozen"):
        outcome = run_policy(
            common, actions[:1], objective, limits,
            policy=policy, max_backend_calls=2, max_depth=1,
        )
        assert {step.parent_id for step in outcome.trace} == {state.label for state in common}

    exact = make_program(
        "exact-phase", 3, [1, 2, 4, 3, 5, 6, 7],
        AngleBinding("theta", "pi/4"), coefficients=[1, 1, 1, -1, -1, -1, 1],
    )
    exact_seeds = construction_seeds(
        exact, CompilationConstraints(4, "unitary_clifford_t"), 1e-4,
        RotationSynthesizer(tmp_path / "exact-rotations.json"),
        FinalObjective(metric="t_depth"),
    )
    exact_seeds = [state for state in exact_seeds if state.lowered.candidate.method == "independent"]
    fixed = run_policy(
        exact_seeds, actions, FinalObjective(metric="t_depth"), SelectionLimits(ancilla=4),
        policy="fixed_count_depth", max_backend_calls=8,
    )
    assert any(step.parent_id != exact_seeds[0].label and step.status == "accepted" for step in fixed.trace)
    assert any(step.action_backend == "phase_ancilla:parallel_phase" and step.a_after > step.a_before for step in fixed.trace)
    assert fixed.best is not None
    assert fixed.best.depth >= 1


def test_search_can_retain_a_worse_feasible_parent_and_respects_budget(tmp_path):
    program = make_program(
        "four", 4, [1, 2, 4, 8], AngleBinding("theta", "0.173")
    )
    objective = FinalObjective.from_value(
        {"mode": "balance", "weights": {"t_count": 0.9, "t_depth": 0.05, "ancilla": 0.05},
         "references": {"t_count": 200, "t_depth": 200, "ancilla": 8}}
    )
    limits = SelectionLimits(ancilla=8)
    seeds = construction_seeds(
        program, CompilationConstraints(8, "unitary_clifford_t", hwp_search_cap=4),
        1e-4, RotationSynthesizer(tmp_path / "rotations2.json"), objective,
    )
    result = run_policy(
        seeds,
        default_actions(PyZXAdapter(seed=0)),
        objective,
        limits,
        policy="fixed_count_depth",
        max_backend_calls=12,
    )
    assert result.backend_calls <= 12
    assert all(limits.violation(state.resources) is None for state in result.archive)
    assert result.best is not None
    assert result.trace
    assert all(step.parent_id for step in result.trace)


def test_search_preserves_hard_limits_and_fixed_objective(tmp_path):
    program = make_program("one", 1, [1], AngleBinding("theta", "pi/4"))
    objective = FinalObjective.from_value(
        {
            "mode": "balance",
            "weights": {"t_count": 1, "t_depth": 1, "ancilla": 1},
            "references": {"t_count": 1, "t_depth": 1, "ancilla": 1},
        }
    )
    limits = SelectionLimits(t_count=1, t_depth=1, ancilla=0)
    seeds = construction_seeds(
        program,
        CompilationConstraints(0, "unitary_clifford_t"),
        1e-4,
        RotationSynthesizer(tmp_path / "rotations.json"),
        objective,
    )
    result = run_policy(
        seeds,
        default_actions(PyZXAdapter(seed=0)),
        objective,
        limits,
        policy="static_balanced",
        max_backend_calls=2,
    )
    assert result.status == "success"
    assert result.objective == objective
    assert result.limits == limits
    assert result.best is not None
    assert limits.violation(result.best.resources) is None


def test_scratch_budget_blocks_and_admits_exact_boundary(tmp_path):
    program = make_program(
        "exact-phase", 3, [1, 2, 4, 3, 5, 6, 7], AngleBinding("theta", "pi/4"),
        coefficients=[1, 1, 1, -1, -1, -1, 1],
    )
    objective = FinalObjective(metric="t_depth")
    seeds = construction_seeds(
        program, CompilationConstraints(4, "unitary_clifford_t"), 1e-4,
        RotationSynthesizer(tmp_path / "boundary.json"), objective,
    )
    seed = next(state for state in seeds if state.lowered.candidate.method == "independent")
    scratch_four = [action for action in default_actions(PyZXAdapter(seed=0)) if action.backend == "phase_ancilla"]
    scratch_four[0] = replace(scratch_four[0], scratch_allowances=(4,))
    rejected = run_policy([seed], scratch_four, objective, SelectionLimits(ancilla=3), policy="adaptive", max_backend_calls=1)
    accepted = run_policy([seed], scratch_four, objective, SelectionLimits(ancilla=4), policy="adaptive", max_backend_calls=1)
    assert rejected.backend_calls == 0
    assert accepted.backend_calls == 1
    assert accepted.best is not None
    assert accepted.best.resource_tuple == (7, 1, 4)


def test_fixed_sequence_continues_after_verified_noop(tmp_path):
    class NoOp:
        def optimize(self, lowered, action):
            return AdapterResult(
                "pyzx", "noop-fixture", action, "verified", 0.0,
                replace(lowered, optimization={"backend": "pyzx", "action": action}),
            )

    program = make_program(
        "exact-phase", 3, [1, 2, 4, 3, 5, 6, 7], AngleBinding("theta", "pi/4"),
        coefficients=[1, 1, 1, -1, -1, -1, 1],
    )
    objective = FinalObjective(metric="t_depth")
    seeds = construction_seeds(
        program, CompilationConstraints(4, "unitary_clifford_t"), 1e-4,
        RotationSynthesizer(tmp_path / "noop.json"), objective,
    )
    seed = next(state for state in seeds if state.lowered.candidate.method == "independent")
    scratch = next(action for action in default_actions(PyZXAdapter(seed=0)) if action.backend == "phase_ancilla")
    actions = [ActionSpec("pyzx:zx_extract", "pyzx", "zx_extract", (1, 0, 0), NoOp()), scratch]
    result = run_policy(
        [seed], actions, objective, SelectionLimits(ancilla=4),
        policy="fixed_count_depth", max_backend_calls=3,
    )
    assert result.trace[0].status == "unchanged"
    assert result.trace[1].parent_id == result.trace[0].output_id
    assert result.trace[1].status == "accepted"
    assert result.best is not None and result.best.depth == 2


def test_rejected_verified_output_keeps_measured_resources_in_trace(tmp_path):
    class OverBudget:
        def optimize(self, lowered, action):
            return AdapterResult(
                "pyzx", "over-budget-fixture", action, "verified", 0.0,
                replace(
                    lowered,
                    events=[*lowered.events, GateEvent("t", (0,)), GateEvent("tdg", (0,))],
                    optimization={"backend": "pyzx", "action": action},
                ),
            )

    program = make_program("one", 1, [1], AngleBinding("theta", "pi/4"))
    objective = FinalObjective(metric="t_count")
    seeds = construction_seeds(
        program, CompilationConstraints(0, "unitary_clifford_t"), 1e-4,
        RotationSynthesizer(tmp_path / "rejected.json"), objective,
    )
    result = run_policy(
        seeds[:1], [ActionSpec("pyzx:basic", "pyzx", "basic", (1, 0, 0), OverBudget())],
        objective, SelectionLimits(t_count=1, t_depth=1, ancilla=0),
        policy="adaptive", max_backend_calls=1,
    )
    assert result.best is not None and result.best.resource_tuple == (1, 1, 0)
    assert result.trace[0].status == "hard_limit"
    assert (result.trace[0].t_after, result.trace[0].d_after, result.trace[0].a_after) == (3, 3, 0)
    assert result.trace[0].j_after == 3


def test_adaptive_priority_recounts_a_real_transformed_parent(tmp_path):
    program = make_program(
        "exact-phase", 3, [1, 2, 4, 3, 5, 6, 7], AngleBinding("theta", "pi/4"),
        coefficients=[1, 1, 1, -1, -1, -1, 1],
    )
    objective = FinalObjective(metric="t_depth")
    seeds = construction_seeds(
        program, CompilationConstraints(4, "unitary_clifford_t"), 1e-4,
        RotationSynthesizer(tmp_path / "priority.json"), objective,
    )
    seed = next(value for value in seeds if value.lowered.candidate.method == "independent")
    actions = default_actions(PyZXAdapter(seed=0))
    actions = [value for value in actions if value.name in {"phase_ancilla:parallel_phase", "pyzx:zx_extract"}]
    result = run_policy(
        [seed], actions, objective, SelectionLimits(t_depth=5, ancilla=4),
        policy="adaptive", max_backend_calls=3,
    )

    first = result.trace[0]
    continuation = result.trace[2]
    assert first.status == "accepted" and first.a_after > first.a_before
    assert continuation.parent_id == first.output_id
    assert continuation.priority_vector[1] < first.priority_vector[1]
    assert continuation.d_before == first.d_after


def test_frozen_preference_matches_initial_regional_scores(tmp_path):
    program = make_program(
        "exact-phase", 3, [1, 2, 4, 3, 5, 6, 7], AngleBinding("theta", "pi/4"),
        coefficients=[1, 1, 1, -1, -1, -1, 1],
    )
    objective = FinalObjective(metric="t_depth")
    limits = SelectionLimits(t_depth=5, ancilla=4)
    seed = next(
        state
        for state in construction_seeds(
            program, CompilationConstraints(4, "unitary_clifford_t"), 1e-4,
            RotationSynthesizer(tmp_path / "frozen.json"), objective,
        )
        if state.lowered.candidate.method == "independent"
    )
    actions = default_actions(PyZXAdapter(seed=0))
    roots = {seed.label: seed}
    adaptive = _proposal_order(
        "adaptive", [seed], actions, objective, limits, set(), roots, 3
    )
    frozen = _proposal_order(
        "frozen", [seed], actions, objective, limits, set(), roots, 3
    )
    adaptive_scores = {
        (item.action.name, item.region, item.allowance):
        (item.priority, item.priority_vector)
        for item in adaptive
    }
    frozen_scores = {
        (item.action.name, item.region, item.allowance):
        (item.priority, item.priority_vector)
        for item in frozen
    }
    assert frozen_scores == adaptive_scores


def test_frozen_preference_uses_current_region_with_initial_vector(tmp_path):
    program = make_program("one", 1, [1], AngleBinding("theta", "pi/4"))
    objective = FinalObjective(metric="t_depth")
    limits = SelectionLimits(t_depth=4, ancilla=4)
    seed = construction_seeds(
        program, CompilationConstraints(0, "unitary_clifford_t"), 1e-4,
        RotationSynthesizer(tmp_path / "frozen-current.json"), objective,
    )[0]
    events = [
        GateEvent("h", (0,)),
        *(GateEvent("t", (0,)) for _ in range(4)),
    ]
    lowered = replace(seed.lowered, events=events)
    transformed = replace(
        seed,
        label="transformed",
        lowered=lowered,
        resources=estimate_resources(lowered),
        schedule=schedule_events(events),
        depth=1,
    )
    action = next(
        item for item in default_actions(PyZXAdapter(seed=0))
        if item.backend == "phase_ancilla"
    )
    frozen_vector = _preference_vector(seed, objective, limits)
    adaptive = _adaptive_priority(
        transformed, action, objective, limits, 1, (1, 5)
    )
    frozen = _adaptive_priority(
        transformed, action, objective, limits, 1, (1, 5),
        preference_vector=frozen_vector,
    )
    assert adaptive[1] == frozen[1]
    assert adaptive[2] != frozen[2]
    assert frozen[2] == frozen_vector


def test_state_identity_includes_validated_clean_pool_capability(tmp_path):
    program = make_program(
        "exact-phase", 3, [1, 2, 4, 3, 5, 6, 7], AngleBinding("theta", "pi/4"),
        coefficients=[1, 1, 1, -1, -1, -1, 1],
    )
    objective = FinalObjective(metric="t_depth")
    source = next(
        state
        for state in construction_seeds(
            program, CompilationConstraints(4, "unitary_clifford_t"), 1e-4,
            RotationSynthesizer(tmp_path / "state-key.json"), objective,
        )
        if state.lowered.candidate.method == "independent"
    )
    optimized = PhaseAncillaAdapter().optimize_region(
        source.lowered, phase_regions(source.lowered.events)[0], 1
    ).lowered
    assert optimized is not None
    with_pool = replace(
        source,
        lowered=optimized,
        resources=estimate_resources(optimized),
    )
    without_pool_lowered = replace(
        optimized,
        optimization={**optimized.optimization, "clean_scratch_pool": []},
    )
    without_pool = replace(with_pool, lowered=without_pool_lowered)
    assert _state_key(with_pool) != _state_key(without_pool)


def test_region_priority_distinguishes_critical_path_from_slack(tmp_path):
    program = make_program("one", 1, [1], AngleBinding("theta", "pi/4"))
    objective = FinalObjective(metric="t_depth")
    seed = construction_seeds(
        program,
        CompilationConstraints(0, "unitary_clifford_t"),
        1e-4,
        RotationSynthesizer(tmp_path / "region-priority.json"),
        objective,
    )[0]
    events = [
        *(GateEvent("t", (0,)) for _ in range(5)),
        GateEvent("h", (2,)),
        *(GateEvent("t", (1,)) for _ in range(3)),
        GateEvent("cx", (1, 2)),
    ]
    lowered = replace(seed.lowered, events=events, allocated_qubits=3)
    state = SearchState(
        label="schedule-witness",
        lowered=lowered,
        resources=estimate_resources(lowered),
        verification=seed.verification,
        objective_value=5,
        source_seed="schedule-witness",
        total_error=1e-4,
        schedule=schedule_events(events),
    )
    action = next(
        item
        for item in default_actions(PyZXAdapter(seed=0))
        if item.backend == "phase_ancilla"
    )
    critical = _adaptive_priority(
        state, action, objective, SelectionLimits(ancilla=4), 1, (0, 5)
    )
    slack = _adaptive_priority(
        state, action, objective, SelectionLimits(ancilla=4), 1, (6, 10)
    )
    assert critical[0] > slack[0]
    assert "5 critical" in critical[1]
    assert "0 critical" in slack[1]
