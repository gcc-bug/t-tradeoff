from __future__ import annotations


# Exact ancilla-free CCX obtained by conjugating the seven-term CCZ phase
# polynomial with H on the target. The three phase rounds realize
# a + b + c - (a xor b) - (a xor c) - (b xor c) + (a xor b xor c).
# See Amy, Maslov, Mosca, and Roetteler, arXiv:1206.0758v4, Figure 13.
_TOFFOLI_TEMPLATE: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (2,)),
    ("t", (0,)),
    ("t", (1,)),
    ("t", (2,)),
    ("cx", (0, 1)),
    ("cx", (0, 2)),
    ("tdg", (1,)),
    ("tdg", (2,)),
    ("cx", (1, 2)),
    ("cx", (0, 1)),
    ("cx", (2, 0)),
    ("t", (0,)),
    ("tdg", (2,)),
    ("cx", (2, 0)),
    ("cx", (1, 2)),
    ("h", (2,)),
)


def exact_toffoli_gate_sequence(
    qubits: tuple[int, ...],
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Return the sourced seven-T, three-T-layer exact Toffoli sequence."""
    if len(qubits) != 3 or len(set(qubits)) != 3:
        raise ValueError("Toffoli requires three distinct wires")
    mapping = dict(enumerate(qubits))
    return tuple(
        (kind, tuple(mapping[qubit] for qubit in template_qubits))
        for kind, template_qubits in _TOFFOLI_TEMPLATE
    )
