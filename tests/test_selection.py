from collective_phase.baselines import (
    compile_hwp_emitted_alternatives,
    compile_independent,
    compile_shared_parity,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.candidates import compile_dependent_triples_raw
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import RotationSynthesizer
from collective_phase.selection import select_lowered_candidate


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
