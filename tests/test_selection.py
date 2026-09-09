import pytest

from collective_phase.baselines import (
    compile_hwp_adder_unitary_alternatives,
    compile_independent,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import RotationSynthesizer
from collective_phase.selection import (
    FinalObjective,
    NoFeasibleAlternativeError,
    SelectionLimits,
    select_lowered_candidate,
)
from collective_phase.verification import LoweredVerificationResult

def test_hwp_selection_uses_fully_lowered_objective():
    program = make_program(
        "five", 3, [1, 2, 3, 5, 6], AngleBinding("theta", "0.173")
    )
    constraints = CompilationConstraints(
        8, "unitary_clifford_t", hwp_search_cap=5
    )
    selected = select_lowered_candidate(
        compile_hwp_adder_unitary_alternatives(program, constraints),
        1e-4,
        RotationSynthesizer(),
        selected_method="hwp_adder_unitary",
        objective="t_count",
    )
    eligible_counts = [
        item.resources.t_count
        for item in selected.alternatives
        if item.eligible
    ]
    assert selected.resources.t_count == min(eligible_counts)
    assert len(selected.alternatives) == 5


def test_three_objectives_use_declared_tie_breaks_and_retain_pareto_set():
    program = make_program(
        "four-adder", 4, [1, 2, 4, 8], AngleBinding("theta", "0.173")
    )
    constraints = CompilationConstraints(
        8, "unitary_clifford_t", hwp_search_cap=4
    )
    alternatives = compile_hwp_adder_unitary_alternatives(program, constraints)
    selections = {
        objective: select_lowered_candidate(
            alternatives,
            1e-4,
            RotationSynthesizer(),
            selected_method="hwp_adder_unitary",
            objective=objective,
            limits={"ancilla": 8, "t_count": 10_000, "t_depth": 10_000},
        )
        for objective in ("t_count", "t_depth", "ancilla")
    }
    for objective, selected in selections.items():
        feasible = [item for item in selected.alternatives if item.feasible]
        if objective == "t_count":
            key = lambda item: (
                item.resources.t_count,
                item.resources.t_depth,
                item.resources.peak_workspace,
                item.label,
            )
        elif objective == "t_depth":
            key = lambda item: (
                item.resources.t_depth,
                item.resources.t_count,
                item.resources.peak_workspace,
                item.label,
            )
        else:
            key = lambda item: (
                item.resources.peak_workspace,
                item.resources.t_count,
                item.resources.t_depth,
                item.label,
            )
        assert selected.candidate.selected_from == min(feasible, key=key).label
        assert selected.nondominated_labels
    assert selections["ancilla"].resources.peak_workspace == 0


def test_balance_objective_uses_fixed_positive_references():
    objective = FinalObjective.from_value(
        {
            "mode": "balance",
            "weights": {"t_count": 1, "t_depth": 2, "ancilla": 0.5},
            "references": {"t_count": 100, "t_depth": 20, "ancilla": 4},
        }
    )
    assert objective.weights == (1.0, 2.0, 0.5)
    assert objective.references == (100.0, 20.0, 4.0)
    assert objective.to_dict()["references"]["ancilla"] == 4.0


@pytest.mark.parametrize(
    "value, message",
    [
        (
            {"mode": "balance", "weights": {}, "references": {}},
            "cannot all be zero",
        ),
        (
            {
                "mode": "balance",
                "weights": {"t_count": 1},
                "references": {"ancilla": 0},
            },
            "references must be positive",
        ),
    ],
)
def test_balance_objective_rejects_invalid_normalization(value, message):
    with pytest.raises(ValueError, match=message):
        FinalObjective.from_value(value)


def test_ancilla_objective_requires_meaningful_other_targets():
    with pytest.raises(ValueError, match="t_count and t_depth limits"):
        FinalObjective(metric="ancilla").validate_limits(SelectionLimits(ancilla=8))


def test_hard_limits_report_no_feasible_alternative_without_relaxing():
    program = make_program("one", 1, [1], AngleBinding("theta", "pi/4"))
    constraints = CompilationConstraints(0, "unitary_clifford_t")
    with pytest.raises(NoFeasibleAlternativeError, match="no feasible alternative"):
        select_lowered_candidate(
            [compile_independent(program, constraints)],
            1e-4,
            RotationSynthesizer(),
            selected_method="selected",
            objective="t_count",
            limits={"t_count": 0},
        )


@pytest.mark.parametrize("value", [True, 1.5, "2", -1])
def test_selection_limits_require_nonnegative_integers(value):
    with pytest.raises(ValueError, match="non-negative integer or null"):
        SelectionLimits(t_count=value)


def test_selection_rejects_unsupported_lowered_evidence(monkeypatch):
    program = make_program("one", 1, [1], AngleBinding("theta", "pi/4"))
    constraints = CompilationConstraints(0, "unitary_clifford_t")
    unsupported = LoweredVerificationResult(
        status="lowered_evidence_unsupported",
        scope="primitive_binding",
        operator_norm_error=None,
        synthesis_error_bound=0.0,
        macro_free=True,
        matrix_bytes=0,
        memory_cap_bytes=1,
        message="test evidence gap",
    )
    monkeypatch.setattr(
        "collective_phase.selection.verify_lowered_circuit",
        lambda lowered, total_error: unsupported,
    )

    with pytest.raises(RuntimeError, match="no eligible emitted alternative"):
        select_lowered_candidate(
            [compile_independent(program, constraints)],
            1e-4,
            RotationSynthesizer(),
            selected_method="selected",
            objective="t_count",
        )
