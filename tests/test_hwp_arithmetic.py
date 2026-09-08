import pytest

from collective_phase.baselines import (
    compile_hwp_emitted,
    compile_hwp_emitted_alternatives,
    compile_hwp_emitted_triple_grouped,
)
from collective_phase.baselines.arithmetic import (
    invert_classical_operations,
    population_count_compute,
    population_count_scratch,
    population_count_width,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import GateEvent, RotationSynthesizer, lower_candidate
from collective_phase.verification import verify_candidate, verify_lowered_circuit


def _apply_classical(bits, operation):
    if operation.kind == "x":
        bits[operation.qubits[0]] ^= 1
    elif operation.kind == "cx":
        control, target = operation.qubits
        bits[target] ^= bits[control]
    elif operation.kind == "toffoli":
        first, second, target = operation.qubits
        bits[target] ^= bits[first] & bits[second]
    else:
        raise AssertionError(operation.kind)


@pytest.mark.parametrize("size", range(1, 9))
def test_population_count_and_inverse_for_all_inputs(size):
    width = population_count_width(size)
    scratch_width = population_count_scratch(size)
    inputs = tuple(range(size))
    outputs = tuple(range(size, size + width))
    scratch = tuple(range(size + width, size + width + scratch_width))
    operations = population_count_compute(inputs, outputs, scratch)
    for value in range(1 << size):
        bits = [(value >> index) & 1 for index in range(size)]
        bits += [0] * (width + scratch_width)
        original = bits.copy()
        for operation in operations:
            _apply_classical(bits, operation)
        actual = sum(
            bits[target] << bit for bit, target in enumerate(outputs)
        )
        assert actual == value.bit_count()
        assert not any(bits[target] for target in scratch)
        for operation in invert_classical_operations(operations):
            _apply_classical(bits, operation)
        assert bits == original


@pytest.mark.parametrize("expression", ["0.173", "pi/4"])
def test_emitted_hwp_is_macro_free_and_verified(expression):
    program = make_program(
        "three", 3, [1, 2, 4], AngleBinding("theta", expression)
    )
    constraints = CompilationConstraints(
        5, "unitary_clifford_t", hwp_search_cap=3
    )
    candidate = compile_hwp_emitted(program, constraints)
    assert candidate.workspace_qubits == 5
    assert verify_candidate(candidate).status == "verified_ideal_semantics"
    lowered = lower_candidate(candidate, 1e-4, RotationSynthesizer())
    assert all(isinstance(event, GateEvent) for event in lowered.events)
    assert (
        verify_lowered_circuit(lowered, 1e-4).status
        == "verified_lowered_dense"
    )


def test_emitted_hwp_workspace_boundary_and_zero_workspace_fallback():
    program = make_program(
        "three", 3, [1, 2, 4], AngleBinding("theta", "0.173")
    )
    bounded = compile_hwp_emitted(
        program, CompilationConstraints(4, "unitary_clifford_t")
    )
    assert bounded.workspace_qubits == 4
    assert [
        item["size"]
        for item in bounded.transformation_trace
        if item["action"] == "emitted_hwp_batch"
    ] == [2]
    direct = compile_hwp_emitted(
        program, CompilationConstraints(0, "unitary_clifford_t")
    )
    assert direct.workspace_qubits == 0
    assert sum(
        operation.kind == "phase" for operation in direct.operations
    ) == 3
    assert verify_candidate(direct).status == "verified_ideal_semantics"


def test_hwp_alternatives_are_distinct_and_bounded():
    program = make_program(
        "four", 4, [1, 2, 4, 8], AngleBinding("theta", "0.173")
    )
    alternatives = compile_hwp_emitted_alternatives(
        program,
        CompilationConstraints(
            9, "unitary_clifford_t", hwp_search_cap=4
        ),
    )
    assert [
        candidate.parameters["batch_limit"] for candidate in alternatives
    ] == [1, 2, 3, 4]
    assert all(candidate.workspace_qubits <= 9 for candidate in alternatives)


def test_emitted_hwp_rejects_measurement_profile_without_relabeling():
    program = make_program("one", 1, [1], AngleBinding("theta", "0.2"))
    candidate = compile_hwp_emitted(
        program,
        CompilationConstraints(2, "measurement_assisted_clifford_t"),
    )
    assert candidate.status == "infeasible"


def test_generic_hwp_can_use_the_candidate_triple_grouping():
    program = make_program(
        "triple", 2, [1, 2, 3, 3], AngleBinding("theta", "0.173")
    )
    candidate = compile_hwp_emitted_triple_grouped(
        program, CompilationConstraints(5, "unitary_clifford_t")
    )
    assert candidate.method == "hwp_emitted_triple_grouped"
    assert candidate.parameters["grouped_triples"] == 0
    assert verify_candidate(candidate).status == "verified_ideal_semantics"

    eligible = make_program(
        "eligible", 2, [1, 2, 3], AngleBinding("theta", "0.173")
    )
    grouped = compile_hwp_emitted_triple_grouped(
        eligible, CompilationConstraints(5, "unitary_clifford_t")
    )
    assert grouped.parameters["grouped_triples"] == 1
    assert any(
        item["action"] == "emitted_hwp_candidate_triple_group"
        for item in grouped.transformation_trace
    )
    assert verify_candidate(grouped).status == "verified_ideal_semantics"
