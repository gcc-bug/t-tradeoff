from collective_phase.adapters import PyZXAdapter
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import RotationSynthesizer
from collective_phase.search import construction_seeds, default_actions, run_policy
from collective_phase.selection import FinalObjective, SelectionLimits


def test_real_circuit_lookahead_exposes_joint_optimization(tmp_path):
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
    without = run_policy(
        seeds,
        actions,
        objective,
        limits,
        policy="adaptive",
        max_backend_calls=2,
    )
    with_lookahead = run_policy(
        seeds,
        actions,
        objective,
        limits,
        policy="adaptive_lookahead",
        max_backend_calls=4,
    )
    assert without.best is not None
    assert with_lookahead.best is not None
    assert with_lookahead.best.resources.t_count < without.best.resources.t_count
    assert with_lookahead.best.lowered.optimization["backend"] == "pyzx"
    assert len(with_lookahead.trace) == 2
    assert with_lookahead.trace[0].provisional is True
    assert with_lookahead.trace[0].j_after > with_lookahead.trace[0].j_before
    assert with_lookahead.trace[1].j_after < with_lookahead.trace[1].j_before
    assert with_lookahead.best.objective_value < without.best.objective_value


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
