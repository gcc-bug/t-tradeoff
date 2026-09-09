import pytest

from collective_phase.baselines import (
    compile_hwp_adder_unitary_alternatives,
    compile_hwp_emitted_alternatives,
    compile_independent,
    compile_shared_parity,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.candidates import compile_dependent_triples_raw
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import RotationSynthesizer
from collective_phase.selection import (
    NoFeasibleAlternativeError,
    SelectionLimits,
    select_lowered_candidate,
)
from collective_phase.verification import LoweredVerificationResult


def _select_triple(expression):
    program = make_program(
        "triple", 2, [1, 2, 3], AngleBinding("theta", expression)
    )
    constraints = CompilationConstraints(8, "unitary_clifford_t")
    return select_lowered_candidate(
        [
            compile_dependent_triples_raw(program, constraints),
            compile_independent(program, constraints),
            compile_shared_parity(program, constraints),
        ],
        1e-4,
        RotationSynthesizer(),
        selected_method="dependent_triples_selected",
        objective="t_count",
        preferred_method="dependent_triples_raw",
    )


def test_exact_angle_regression_selects_direct_fallback():
    selected = _select_triple("pi/4")
    assert not selected.candidate.selected_from.startswith(
        "dependent_triples_raw:"
    )
    assert selected.candidate.method == "dependent_triples_selected"
    assert selected.resources.t_count == 3
    assert len(selected.alternatives) == 3


def test_generic_angle_selects_raw_rewrite_and_retains_all_alternatives():
    selected = _select_triple("0.173")
    assert selected.candidate.selected_from.startswith(
        "dependent_triples_raw:"
    )
    assert selected.candidate.parameters["used_rewrite"] is True
    assert len(selected.candidate.parameters["selection_alternatives"]) == 3
    assert selected.candidate.parameters["nondominated_alternatives"]


def test_hwp_selection_uses_fully_lowered_objective():
    program = make_program(
        "five", 3, [1, 2, 3, 5, 6], AngleBinding("theta", "0.173")
    )
    constraints = CompilationConstraints(
        8, "unitary_clifford_t", hwp_search_cap=5
    )
    selected = select_lowered_candidate(
        compile_hwp_emitted_alternatives(program, constraints),
        1e-4,
        RotationSynthesizer(),
        selected_method="hwp_emitted",
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
            limits={"ancilla": 8},
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
