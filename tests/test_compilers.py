import pytest

from collective_phase.baselines import (
    compile_hwp_adder_unitary,
    compile_independent,
    compile_shared_parity,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, ParityTerm, PhaseBlock, PhaseProgram, make_program
from collective_phase.verification import verify_candidate, verify_dense_action


UNITARY = CompilationConstraints(32, "unitary_clifford_t")


@pytest.mark.parametrize(
    "masks",
    [[], [1], [3, 3], [1, 2, 3], [1, 2, 3, 5, 6], [3, 5, 6, 9, 10]],
)
@pytest.mark.parametrize(
    "compiler",
    [
        compile_independent,
        compile_shared_parity,
        compile_hwp_adder_unitary,
    ],
)
def test_compilers_restore_workspace_and_phase(masks, compiler):
    qubits = max(1, max(masks, default=0).bit_length())
    program = make_program("case", qubits, masks, AngleBinding("theta", "0.173"))
    candidate = compiler(program, UNITARY)
    result = verify_candidate(candidate)
    expected = (
        "verified_ideal_semantics"
        if candidate.accounting_status == "emitted"
        else "verified_ideal_macro_semantics"
    )
    assert result.status == expected
    if qubits + candidate.workspace_qubits <= 10:
        assert verify_dense_action(candidate) < 1e-10


def test_hwp_non_power_of_two_and_bounded_balanced_batches():
    program = make_program("five", 3, [1, 2, 3, 5, 6], AngleBinding("theta", "0.619"))
    candidate = compile_hwp_adder_unitary(
        program, CompilationConstraints(5, "unitary_clifford_t", "balanced")
    )
    assert candidate.status == "success"
    assert candidate.workspace_qubits <= 5
    assert verify_candidate(candidate).status == "verified_ideal_semantics"
    sizes = [
        value["size"]
        for value in candidate.transformation_trace
        if value["action"] == "hwp_adder_unitary_batch"
    ]
    assert sizes == [3, 2]


def test_hwp_uses_direct_fallback_at_zero_workspace():
    program = make_program("one", 1, [1], AngleBinding("theta", "0.2"))
    candidate = compile_hwp_adder_unitary(
        program, CompilationConstraints(0, "unitary_clifford_t")
    )
    assert candidate.status == "success"
    assert candidate.workspace_qubits == 0
    assert candidate.accounting_status == "emitted"
    assert verify_candidate(candidate).status == "verified_ideal_semantics"


def test_weighted_hwp_partitions_compatible_coefficients():
    program = make_program(
        "weighted", 2, [1, 2], AngleBinding("theta", "0.2"), coefficients=[1, 2]
    )
    candidate = compile_hwp_adder_unitary(program, UNITARY)
    assert candidate.status == "success"
    assert candidate.workspace_qubits == 0
    assert sum(operation.kind == "phase" for operation in candidate.operations) == 2
    assert verify_candidate(candidate).status == "verified_ideal_semantics"
    assert (
        verify_candidate(compile_independent(program, UNITARY)).status
        == "verified_ideal_semantics"
    )


def test_affine_sign_and_constant_phase_compile_exactly():
    angle = AngleBinding("theta", "0.31")
    program = PhaseProgram(
        "affine",
        2,
        (angle,),
        (
            PhaseBlock(
                "block",
                (
                    ParityTerm("constant", 0, "theta", offset=True),
                    ParityTerm("complement", 3, "theta", offset=True),
                ),
            ),
        ),
    )
    for compiler in (compile_independent, compile_shared_parity, compile_hwp_adder_unitary):
        assert (
            verify_candidate(compiler(program, UNITARY)).status
            == "verified_ideal_semantics"
        )
