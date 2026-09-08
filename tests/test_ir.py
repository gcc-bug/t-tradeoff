import math

import pytest

from collective_phase.ir import AngleBinding, ParityTerm, PhaseBlock, PhaseProgram, make_program


def test_angle_classes_are_exact_ids_not_float_buckets():
    first = AngleBinding("a", "0.173")
    second = AngleBinding("b", "0.17300000000000001")
    program = PhaseProgram(
        "angles",
        1,
        (first, second),
        (
            PhaseBlock(
                "b",
                (
                    ParityTerm("t0", 1, "a"),
                    ParityTerm("t1", 1, "b"),
                ),
            ),
        ),
    )
    groups, _, _ = program.normalized_groups()
    assert len(groups) == 2


def test_affine_normalization_preserves_phase_and_global_constant():
    angle = AngleBinding("theta", "pi/4")
    program = PhaseProgram(
        "affine",
        1,
        (angle,),
        (PhaseBlock("b", (ParityTerm("t", 1, "theta", offset=True),)),),
    )
    groups, global_phase, _ = program.normalized_groups()
    assert groups == {(1, "theta"): -1}
    assert global_phase == pytest.approx(math.pi / 4)
    assert program.integer_values(0) == {"theta": 1}
    assert program.integer_values(1) == {"theta": 0}


def test_duplicate_terms_are_preserved_in_ir_and_combined_only_by_compiler_view():
    program = make_program("dup", 2, [3, 3], AngleBinding("theta", "0.2"))
    assert len(program.terms) == 2
    groups, _, _ = program.normalized_groups()
    assert groups == {(3, "theta"): 2}


def test_rejects_mask_outside_declared_register():
    with pytest.raises(ValueError, match="mask exceeds"):
        make_program("bad", 2, [4], AngleBinding("theta", "0.2"))

