import cmath

import pytest

from collective_phase.ir import (
    AngleBinding,
    ParityTerm,
    PhaseBlock,
    PhaseProgram,
)
from collective_phase.preprocessing import PREPROCESSING_VERSION, preprocess


def _phase_distance(first, second):
    return abs(cmath.exp(1j * first) - cmath.exp(1j * second))


def test_empty_program_has_canonical_empty_representation():
    program = PhaseProgram("empty", 0, (), ())
    normalized = preprocess(program)
    assert normalized.version == PREPROCESSING_VERSION
    assert normalized.terms == ()
    assert normalized.groups == ()
    assert normalized.global_phase == 0


def test_constants_complements_duplicates_and_cancellation_preserve_phase():
    angles = (
        AngleBinding("a", "0.173"),
        AngleBinding("b", "0.17300000000000001"),
    )
    blocks = (
        PhaseBlock(
            "first",
            (
                ParityTerm(
                    "constant-one", 0, "a", offset=True, coefficient=2
                ),
                ParityTerm("constant-zero", 0, "a"),
                ParityTerm(
                    "complement", 1, "a", offset=True, coefficient=3
                ),
                ParityTerm("duplicate", 1, "a", coefficient=2),
                ParityTerm("cancels", 2, "a", coefficient=-4),
                ParityTerm("cancels-too", 2, "a", coefficient=4),
                ParityTerm("other-angle", 1, "b", coefficient=7),
            ),
        ),
        PhaseBlock(
            "second",
            (
                ParityTerm(
                    "same-mask-new-block", 1, "a", coefficient=-1
                ),
            ),
        ),
    )
    program = PhaseProgram("mixed", 2, angles, blocks)
    normalized = preprocess(program)
    assert [
        (term.block_id, term.mask, term.angle_id, term.coefficient)
        for term in normalized.terms
    ] == [
        ("first", 1, "a", -1),
        ("first", 1, "b", 7),
        ("second", 1, "a", -1),
    ]
    assert len(normalized.groups) == 3
    assert {group.block_id for group in normalized.groups} == {
        "first",
        "second",
    }
    assert any(
        item["action"] == "constant_eliminated"
        for item in normalized.trace
    )
    assert any(
        item["action"] == "affine_complement_normalized"
        for item in normalized.trace
    )
    assert any(
        item["action"] == "duplicate_cancellation"
        for item in normalized.trace
    )
    for x in range(1 << program.qubit_count):
        assert (
            _phase_distance(
                program.phase_radians(x),
                normalized.phase_radians(program, x),
            )
            < 1e-12
        )


def test_equal_numeric_values_with_distinct_angle_ids_do_not_merge():
    program = PhaseProgram(
        "classes",
        1,
        (
            AngleBinding("left", "0.2"),
            AngleBinding("right", "0.2"),
        ),
        (
            PhaseBlock(
                "b",
                (
                    ParityTerm("l", 1, "left"),
                    ParityTerm("r", 1, "right"),
                ),
            ),
        ),
    )
    normalized = preprocess(program)
    assert len(normalized.groups) == 2
    assert {group.angle_id for group in normalized.groups} == {
        "left",
        "right",
    }


def test_preprocessing_does_not_extend_to_non_diagonal_blocks():
    with pytest.raises(ValueError, match="unsupported block boundary"):
        PhaseProgram(
            "bad",
            1,
            (AngleBinding("a", "0.1"),),
            (PhaseBlock("b", (), boundary="mixer"),),
        )
