from __future__ import annotations

from itertools import combinations

from ..circuit import Operation


def population_count_width(input_count: int) -> int:
    if input_count < 1:
        raise ValueError("population count requires at least one input")
    return input_count.bit_length()


def population_count_scratch(input_count: int) -> int:
    if input_count < 2:
        return 0
    largest_degree = 1 << (input_count.bit_length() - 1)
    return max(0, largest_degree - 2)


def emitted_hwp_workspace(input_count: int) -> int:
    if input_count <= 1:
        return 0
    return (
        input_count
        + population_count_width(input_count)
        + population_count_scratch(input_count)
    )


def append_multi_controlled_x(
    operations: list[Operation],
    controls: tuple[int, ...],
    target: int,
    scratch: tuple[int, ...],
) -> None:
    """Toggle target by the AND of controls and restore clean scratch."""
    if target in controls or target in scratch or set(controls) & set(scratch):
        raise ValueError("multi-controlled X wires must be distinct")
    if not controls:
        operations.append(Operation("x", (target,)))
        return
    if len(controls) == 1:
        operations.append(Operation("cx", (controls[0], target)))
        return
    if len(controls) == 2:
        operations.append(Operation("toffoli", (controls[0], controls[1], target)))
        return
    required = len(controls) - 2
    if len(scratch) < required:
        raise ValueError(
            f"{len(controls)}-controlled X requires {required} clean scratch qubits"
        )
    work = scratch[:required]
    operations.append(Operation("toffoli", (controls[0], controls[1], work[0])))
    for index in range(2, len(controls) - 1):
        operations.append(
            Operation("toffoli", (controls[index], work[index - 2], work[index - 1]))
        )
    operations.append(
        Operation("toffoli", (controls[-1], work[-1], target))
    )
    for index in reversed(range(2, len(controls) - 1)):
        operations.append(
            Operation("toffoli", (controls[index], work[index - 2], work[index - 1]))
        )
    operations.append(Operation("toffoli", (controls[0], controls[1], work[0])))


def population_count_compute(
    inputs: tuple[int, ...],
    outputs: tuple[int, ...],
    scratch: tuple[int, ...],
) -> list[Operation]:
    """Out-of-place popcount via elementary symmetric polynomials over GF(2).

    Output bit j is the XOR of every monomial of degree 2**j in the input
    bits. This is the binary-weight identity implied by Lucas' theorem.
    Inputs are preserved; outputs and scratch must start at zero. Scratch is
    restored after every monomial.
    """
    expected_width = population_count_width(len(inputs))
    if len(outputs) != expected_width:
        raise ValueError(
            f"population count needs {expected_width} output bits, got {len(outputs)}"
        )
    if len(scratch) < population_count_scratch(len(inputs)):
        raise ValueError("insufficient population-count scratch")
    if len(set(inputs + outputs + scratch)) != len(inputs + outputs + scratch):
        raise ValueError("population-count registers must be disjoint")
    operations: list[Operation] = []
    for bit, target in enumerate(outputs):
        degree = 1 << bit
        for controls in combinations(inputs, degree):
            append_multi_controlled_x(operations, controls, target, scratch)
    return operations


def invert_classical_operations(operations: list[Operation]) -> list[Operation]:
    if any(operation.kind not in {"x", "cx", "toffoli"} for operation in operations):
        raise ValueError("only self-inverse classical gates can be inverted here")
    return list(reversed(operations))
