from __future__ import annotations

import cmath
from fractions import Fraction
import math

import pyzx
from pyzx import Circuit
from pyzx.utils import EdgeType

from ..lowering import GateEvent, MacroEvent


def events_to_circuit(
    events: list[GateEvent | MacroEvent], qubit_count: int
) -> Circuit:
    circuit = Circuit(qubit_count)
    for event in events:
        if isinstance(event, MacroEvent):
            raise ValueError("external optimizers require a fully emitted gate stream")
        qubits = event.qubits
        if event.kind == "h":
            circuit.add_gate("HAD", qubits[0])
        elif event.kind == "x":
            circuit.add_gate("NOT", qubits[0])
        elif event.kind == "z":
            circuit.add_gate("Z", qubits[0])
        elif event.kind == "s":
            circuit.add_gate("S", qubits[0])
        elif event.kind == "sdg":
            circuit.add_gate("S", qubits[0], adjoint=True)
        elif event.kind == "t":
            circuit.add_gate("T", qubits[0])
        elif event.kind == "tdg":
            circuit.add_gate("T", qubits[0], adjoint=True)
        elif event.kind == "cx":
            circuit.add_gate("CNOT", qubits[0], qubits[1])
        else:
            raise ValueError(f"PyZX adapter does not support gate {event.kind!r}")
    return circuit


def _phase_events(target: int, phase: Fraction | int) -> list[GateEvent]:
    value = Fraction(phase) % 2
    quarters = value * 4
    if quarters.denominator != 1:
        raise ValueError(f"optimizer returned non-Clifford+T phase {phase}")
    return {
        0: [],
        1: [GateEvent("t", (target,))],
        2: [GateEvent("s", (target,))],
        3: [GateEvent("s", (target,)), GateEvent("t", (target,))],
        4: [GateEvent("z", (target,))],
        5: [GateEvent("z", (target,)), GateEvent("t", (target,))],
        6: [GateEvent("sdg", (target,))],
        7: [GateEvent("tdg", (target,))],
    }[int(quarters)]


def circuit_to_events(circuit: Circuit) -> list[GateEvent]:
    events: list[GateEvent] = []
    for gate in circuit.to_basic_gates().gates:
        kind = type(gate).__name__
        if kind == "HAD":
            events.append(GateEvent("h", (gate.target,)))
        elif kind == "NOT":
            events.append(GateEvent("x", (gate.target,)))
        elif kind == "Z":
            events.append(GateEvent("z", (gate.target,)))
        elif kind in {"S", "T", "ZPhase"}:
            events.extend(_phase_events(gate.target, gate.phase))
        elif kind == "CNOT":
            events.append(GateEvent("cx", (gate.control, gate.target)))
        elif kind == "CZ":
            events.extend(
                [
                    GateEvent("h", (gate.target,)),
                    GateEvent("cx", (gate.control, gate.target)),
                    GateEvent("h", (gate.target,)),
                ]
            )
        elif kind == "SWAP":
            events.extend(
                [
                    GateEvent("cx", (gate.control, gate.target)),
                    GateEvent("cx", (gate.target, gate.control)),
                    GateEvent("cx", (gate.control, gate.target)),
                ]
            )
        else:
            raise ValueError(f"optimizer returned unsupported gate {kind!r}")
    return events


def equivalence_phase(source: Circuit, result: Circuit) -> float:
    if not source.verify_equality(result, up_to_global_phase=True):
        raise ValueError("PyZX could not verify optimizer output equivalence")
    comparison = source.adjoint()
    comparison.add_circuit(result)
    graph = comparison.to_graph()
    pyzx.simplify.full_reduce(graph, quiet=True)
    identity = (
        graph.num_vertices() == source.qubits * 2
        and all(graph.edge_type(edge) == EdgeType.SIMPLE for edge in graph.edges())
        and all(
            graph.connected(left, right)
            for left, right in zip(graph.inputs(), graph.outputs(), strict=True)
        )
    )
    if not identity:
        raise ValueError("PyZX equivalence reduction did not reach the identity")
    scalar = graph.scalar.to_number()
    if not math.isclose(abs(scalar), 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("optimizer equivalence has a non-unit scalar")
    return cmath.phase(scalar)
