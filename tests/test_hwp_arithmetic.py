import pytest

from collective_phase.baselines import (
    compile_hwp_adder_unitary,
    compile_hwp_adder_unitary_alternatives,
)
from collective_phase.baselines.arithmetic import (
    append_three_to_two_compressor,
    append_two_to_two_adder,
    hamming_weight_compute,
    hwp_adder_workspace,
    hwp_compressor_count,
    invert_classical_operations,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, make_program
from collective_phase.verification import verify_candidate


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


def test_adder_compressor_primitive_truth_tables():
    operations = []
    append_three_to_two_compressor(operations, 0, 1, 2, 3)
    for value in range(8):
        bits = [(value >> index) & 1 for index in range(3)] + [0]
        original = bits.copy()
        for operation in operations:
            _apply_classical(bits, operation)
        assert bits[:2] == original[:2]
        assert bits[2] + 2 * bits[3] == sum(original[:3])

    operations = []
    append_two_to_two_adder(operations, 0, 1, 2)
    for value in range(4):
        bits = [(value >> index) & 1 for index in range(2)] + [0]
        original = bits.copy()
        for operation in operations:
            _apply_classical(bits, operation)
        assert bits[0] == original[0]
        assert bits[1] + 2 * bits[2] == sum(original[:2])


@pytest.mark.parametrize("size", range(1, 9))
def test_adder_hamming_weight_and_inverse_for_all_inputs(size):
    carry_count = hwp_compressor_count(size)
    inputs = tuple(range(size))
    carries = tuple(range(size, size + carry_count))
    operations, layout = hamming_weight_compute(inputs, carries)
    assert sum(operation.kind == "toffoli" for operation in operations) == carry_count
    for value in range(1 << size):
        bits = [(value >> index) & 1 for index in range(size)] + [0] * carry_count
        original = bits.copy()
        for operation in operations:
            _apply_classical(bits, operation)
        actual = sum(
            bits[target] << bit
            for bit, target in enumerate(layout.output_qubits)
        )
        assert actual == value.bit_count()
        for operation in invert_classical_operations(operations):
            _apply_classical(bits, operation)
        assert bits == original


@pytest.mark.parametrize("size", range(1, 9))
def test_adder_hwp_emits_linear_arithmetic_and_unitary_cleanup(size):
    program = make_program(
        f"adder-{size}",
        size,
        [1 << index for index in range(size)],
        AngleBinding("theta", "pi/4"),
    )
    candidate = compile_hwp_adder_unitary(
        program,
        CompilationConstraints(None, "unitary_clifford_t", hwp_search_cap=8),
    )
    expected_compressors = hwp_compressor_count(size)
    assert candidate.workspace_qubits == hwp_adder_workspace(size)
    assert sum(operation.kind == "toffoli" for operation in candidate.operations) == (
        2 * expected_compressors
    )
    assert sum(operation.kind == "phase" for operation in candidate.operations) == (
        size.bit_length() if size > 1 else 1
    )
    assert verify_candidate(candidate).status == "verified_ideal_semantics"


def test_adder_hwp_alternatives_record_distinct_batch_limits():
    program = make_program(
        "five-adder", 5, [1, 2, 4, 8, 16], AngleBinding("theta", "0.173")
    )
    alternatives = compile_hwp_adder_unitary_alternatives(
        program,
        CompilationConstraints(8, "unitary_clifford_t", hwp_search_cap=5),
    )
    assert [item.parameters["batch_limit"] for item in alternatives] == [1, 2, 3, 4, 5]
    assert all(item.workspace_qubits <= 8 for item in alternatives)


def test_adder_hwp_rejects_measurement_profile_without_relabeling():
    program = make_program("one", 1, [1], AngleBinding("theta", "0.2"))
    candidate = compile_hwp_adder_unitary(
        program,
        CompilationConstraints(2, "measurement_assisted_clifford_t"),
    )
    assert candidate.status == "infeasible"
