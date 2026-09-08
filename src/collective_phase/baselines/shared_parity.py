from __future__ import annotations

from collections import defaultdict

from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from .common import CompilationConstraints


def compile_shared_parity(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    groups, global_phase, trace = program.normalized_groups()
    by_anchor: dict[int, list[tuple[int, str, int]]] = defaultdict(list)
    for (mask, angle_id), coefficient in groups.items():
        anchor = (mask & -mask).bit_length() - 1
        by_anchor[anchor].append((mask, angle_id, coefficient))

    operations: list[Operation] = []
    order_trace: list[dict] = []
    for anchor in sorted(by_anchor):
        current = 1 << anchor
        pending = list(by_anchor[anchor])
        emitted: list[int] = []
        while pending:
            choice = min(
                pending,
                key=lambda item: (((current ^ item[0]) & ~(1 << anchor)).bit_count(), item),
            )
            pending.remove(choice)
            mask, angle_id, coefficient = choice
            delta = (current ^ mask) & ~(1 << anchor)
            for control in range(program.qubit_count):
                if (delta >> control) & 1:
                    operations.append(Operation("cx", (control, anchor)))
            operations.append(Operation("phase", (anchor,), angle_id, coefficient))
            current = mask
            emitted.append(mask)
        delta = current ^ (1 << anchor)
        for control in reversed(range(program.qubit_count)):
            if (delta >> control) & 1:
                operations.append(Operation("cx", (control, anchor)))
        order_trace.append({"anchor": anchor, "mask_order": emitted})
    trace.append({"action": "anchor_parity_walk", "groups": order_trace})
    return Candidate(
        method="shared_parity",
        version="0.1",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=0,
        global_phase=global_phase,
        model_profile=constraints.model_profile,
        parameters={"walk": "greedy_hamming_distance", "workspace_budget": constraints.workspace_budget},
        transformation_trace=trace,
        proof_obligations=["each anchor row is restored to its basis vector"],
    )

