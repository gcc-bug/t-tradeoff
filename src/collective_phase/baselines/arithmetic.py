from __future__ import annotations

from dataclasses import dataclass
from ..circuit import Operation

@dataclass(frozen=True)
class HammingWeightLayout:
    """Wires retained after a staged compressor network has run."""

    output_qubits: tuple[int, ...]
    garbage_qubits: tuple[int, ...]
    carry_qubits: tuple[int, ...]
    stage_widths: tuple[int, ...]


def hwp_compressor_count(input_count: int) -> int:
    """Exact number of one-carry compressors in the staged HWP network."""
    if input_count < 1:
        raise ValueError("HWP compression requires at least one input")
    return input_count - input_count.bit_count()


def hwp_adder_workspace(input_count: int) -> int:
    """Parity materialization plus carries for the unitary HWP adaptation."""
    if input_count <= 1:
        return 0
    return input_count + hwp_compressor_count(input_count)


def append_three_to_two_compressor(
    operations: list[Operation], a: int, b: int, c: int, carry: int
) -> None:
    """Map three equal-weight bits to their parity and a clean carry bit.

    The wires ``a`` and ``b`` are retained as garbage, ``c`` becomes the low
    sum bit, and ``carry`` becomes the high bit. All four wires must differ and
    the carry must start in zero.
    """
    if len({a, b, c, carry}) != 4:
        raise ValueError("3-to-2 compressor wires must be distinct")
    operations.extend(
        [
            Operation("cx", (a, b)),
            Operation("cx", (a, c)),
            Operation("toffoli", (b, c, carry)),
            Operation("cx", (a, b)),
            Operation("cx", (a, carry)),
            Operation("cx", (b, c)),
        ]
    )


def append_two_to_two_adder(
    operations: list[Operation], a: int, b: int, carry: int
) -> None:
    """Map two equal-weight bits to a sum bit and a clean carry bit."""
    if len({a, b, carry}) != 3:
        raise ValueError("2-to-2 adder wires must be distinct")
    operations.extend(
        [
            Operation("toffoli", (a, b, carry)),
            Operation("cx", (a, b)),
        ]
    )


def hamming_weight_compute(
    inputs: tuple[int, ...], carries: tuple[int, ...]
) -> tuple[list[Operation], HammingWeightLayout]:
    """Emit the staged adder/compressor Hamming-weight construction.

    This follows Kivlichan et al., arXiv:1902.10673v4, Appendix A.1: reduce
    equal-weight bits in triples, handle an even final pair with a half adder,
    and repeat on the carries. Inputs may be overwritten because the caller
    reverses the emitted operations after phasing the surviving weight bits.
    """
    if not inputs:
        raise ValueError("Hamming-weight computation requires at least one input")
    required = hwp_compressor_count(len(inputs))
    if len(carries) != required:
        raise ValueError(f"Hamming-weight computation needs {required} clean carries")
    if len(set(inputs + carries)) != len(inputs + carries):
        raise ValueError("Hamming-weight input and carry registers must be disjoint")

    operations: list[Operation] = []
    available = iter(carries)
    active = list(inputs)
    outputs: list[int] = []
    stage_widths: list[int] = []
    while active:
        stage_widths.append(len(active))
        next_weight: list[int] = []
        for index in range(0, len(active) - 2, 2):
            carry = next(available)
            append_three_to_two_compressor(
                operations,
                active[index],
                active[index + 1],
                active[index + 2],
                carry,
            )
            next_weight.append(carry)
        if len(active) % 2:
            outputs.append(active[-1])
        else:
            carry = next(available)
            append_two_to_two_adder(operations, active[-2], active[-1], carry)
            outputs.append(active[-1])
            next_weight.append(carry)
        active = next_weight

    try:
        next(available)
    except StopIteration:
        pass
    else:
        raise AssertionError("not all HWP carry wires were consumed")
    output_set = set(outputs)
    garbage = tuple(wire for wire in inputs + carries if wire not in output_set)
    return operations, HammingWeightLayout(
        output_qubits=tuple(outputs),
        garbage_qubits=garbage,
        carry_qubits=carries,
        stage_widths=tuple(stage_widths),
    )


def invert_classical_operations(operations: list[Operation]) -> list[Operation]:
    if any(operation.kind not in {"x", "cx", "toffoli"} for operation in operations):
        raise ValueError("only self-inverse classical gates can be inverted here")
    return list(reversed(operations))
