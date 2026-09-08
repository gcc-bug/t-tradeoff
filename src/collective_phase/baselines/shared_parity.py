from __future__ import annotations

from collections import defaultdict

from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from ..preprocessing import PREPROCESSING_VERSION, preprocess
from .common import CompilationConstraints


def compile_shared_parity(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    normalized = preprocess(program)
    by_block_anchor: dict[tuple[str, int], list] = defaultdict(list)
    for term in normalized.terms:
        anchor = (term.mask & -term.mask).bit_length() - 1
        by_block_anchor[(term.block_id, anchor)].append(term)

    operations: list[Operation] = []
    order_trace: list[dict] = []
    for block_id, anchor in sorted(by_block_anchor):
        current = 1 << anchor
        pending = list(by_block_anchor[(block_id, anchor)])
        emitted: list[int] = []
        while pending:
            choice = min(
                pending,
                key=lambda item: (
                    ((current ^ item.mask) & ~(1 << anchor)).bit_count(),
                    item.mask,
                    item.angle_id,
                ),
            )
            pending.remove(choice)
            mask = choice.mask
            delta = (current ^ mask) & ~(1 << anchor)
            for control in range(program.qubit_count):
                if (delta >> control) & 1:
                    operations.append(Operation("cx", (control, anchor)))
            operations.append(
                Operation(
                    "phase",
                    (anchor,),
                    choice.angle_id,
                    choice.coefficient,
                )
            )
            current = mask
            emitted.append(mask)
        delta = current ^ (1 << anchor)
        for control in reversed(range(program.qubit_count)):
            if (delta >> control) & 1:
                operations.append(Operation("cx", (control, anchor)))
        order_trace.append(
            {"block_id": block_id, "anchor": anchor, "mask_order": emitted}
        )
    trace = list(normalized.trace)
    trace.append({"action": "anchor_parity_walk", "groups": order_trace})
    return Candidate(
        method="shared_parity",
        version="0.1",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=0,
        global_phase=normalized.global_phase,
        model_profile=constraints.model_profile,
        parameters={"walk": "greedy_hamming_distance", "workspace_budget": constraints.workspace_budget},
        transformation_trace=trace,
        proof_obligations=["each anchor row is restored to its basis vector"],
        implementation_family="direct",
        variant="normalized_greedy_anchor_walk",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )
