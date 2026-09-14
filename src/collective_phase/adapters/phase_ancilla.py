"""Limited clean-scratch phase-polynomial resynthesis (AMM-style reproduction).

Only contiguous CNOT/diagonal Clifford+T regions are eligible. All original
wires are treated as arbitrary live inputs; fresh scratch is returned to zero.
"""

from collections import defaultdict
from dataclasses import replace
import time

from ..lowering import GateEvent, LoweredCircuit
from .common import AdapterResult


PHASE_GATES = {"t": 1, "tdg": -1, "s": 2, "sdg": -2, "z": 4}
REGION_GATES = frozenset(PHASE_GATES) | {"cx"}


def phase_signature(events: list, live: int, width: int) -> tuple[tuple[int, ...], tuple[tuple[int, int], ...]]:
    """Linear output masks and phase polynomial mod 8 on clean extra wires."""
    if width < live:
        raise ValueError("replacement has fewer wires than its live interface")
    masks = [1 << wire for wire in range(live)] + [0] * (width - live)
    phases: dict[int, int] = defaultdict(int)
    for event in events:
        if not isinstance(event, GateEvent) or event.kind not in REGION_GATES:
            raise ValueError("unsupported phase region")
        if any(wire < 0 or wire >= width for wire in event.qubits):
            raise ValueError("phase region references an out-of-range wire")
        if event.kind == "cx":
            if len(event.qubits) != 2 or event.qubits[0] == event.qubits[1]:
                raise ValueError("invalid CNOT in phase region")
            control, target = event.qubits
            masks[target] ^= masks[control]
        else:
            if len(event.qubits) != 1:
                raise ValueError("invalid phase gate")
            phases[masks[event.qubits[0]]] += PHASE_GATES[event.kind]
    return tuple(masks), tuple(sorted((mask, value % 8) for mask, value in phases.items() if value % 8))


def phase_regions(events: list) -> list[tuple[int, int]]:
    regions = []
    start = 0
    for index in range(len(events) + 1):
        if index < len(events) and isinstance(events[index], GateEvent) and events[index].kind in REGION_GATES:
            continue
        if index - start > 3 and sum(event.kind in {"t", "tdg"} for event in events[start:index]) >= 3:
            regions.append((start, index))
        start = index + 1
    return regions


def _phase_gates(power: int, wire: int) -> list[GateEvent]:
    return {
        0: [], 1: [GateEvent("t", (wire,))],
        2: [GateEvent("s", (wire,))],
        3: [GateEvent("s", (wire,)), GateEvent("t", (wire,))],
        4: [GateEvent("z", (wire,))],
        5: [GateEvent("z", (wire,)), GateEvent("t", (wire,))],
        6: [GateEvent("sdg", (wire,))],
        7: [GateEvent("tdg", (wire,))],
    }[power]


class PhaseAncillaAdapter:
    revision = "amm-phase-polynomial-limited-v1"

    def optimize_region(
        self, lowered: LoweredCircuit, region: tuple[int, int], allowance: int
    ) -> AdapterResult:
        started = time.perf_counter()
        try:
            if allowance <= 0 or region not in phase_regions(lowered.events):
                raise ValueError("no supported phase region or scratch allowance")
            live = lowered.allocated_qubits
            if live is None:
                live = lowered.candidate.program.qubit_count + lowered.candidate.workspace_qubits
            original = lowered.events[region[0]:region[1]]
            _, phases = phase_signature(original, live, live)
            direct = [(mask, power) for mask, power in phases if mask.bit_count() == 1]
            indirect = [(mask, power) for mask, power in phases if mask.bit_count() > 1]
            if len(indirect) < 2:
                raise ValueError("region has fewer than two nontrivial phase parities")
            scratch = min(allowance, len(indirect))
            rewritten: list[GateEvent] = []
            for offset in range(0, len(indirect), scratch):
                group = indirect[offset:offset + scratch]
                for index, (mask, _) in enumerate(group):
                    rewritten.extend(GateEvent("cx", (wire, live + index)) for wire in range(live) if mask & (1 << wire))
                if offset == 0:
                    for mask, power in direct:
                        rewritten.extend(_phase_gates(power, mask.bit_length() - 1))
                for index, (mask, power) in enumerate(group):
                    rewritten.extend(_phase_gates(power, live + index))
                for index, (mask, _) in reversed(list(enumerate(group))):
                    rewritten.extend(GateEvent("cx", (wire, live + index)) for wire in reversed(range(live)) if mask & (1 << wire))
            rewritten.extend(event for event in original if event.kind == "cx")
            if phase_signature(rewritten, live, live + scratch) != (
                phase_signature(original, live, live)[0] + (0,) * scratch,
                phases,
            ):
                raise ValueError("phase replacement failed its clean-scratch contract")
            events = [*lowered.events[:region[0]], *rewritten, *lowered.events[region[1]:]]
            optimized = replace(
                lowered, events=events, allocated_qubits=live + scratch,
                optimization={"backend": "phase_ancilla", "revision": self.revision,
                              "action": "parallel_phase", "region": list(region),
                              "scratch": scratch, "contract": "clean_phase_polynomial"},
            )
            return AdapterResult("phase_ancilla", self.revision, "parallel_phase", "verified", time.perf_counter() - started, optimized)
        except (ValueError, TypeError) as exc:
            return AdapterResult("phase_ancilla", self.revision, "parallel_phase", "failed", time.perf_counter() - started, reason=str(exc))
