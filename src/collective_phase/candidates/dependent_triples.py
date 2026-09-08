from __future__ import annotations

from collections import defaultdict

from ..baselines.common import CompilationConstraints, append_parity_into, append_parity_phase
from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from ..profiles import dependent_triples


def compile_dependent_triples(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    groups, global_phase, trace = program.normalized_groups()
    eligible: dict[str, set[int]] = defaultdict(set)
    for (mask, angle_id), coefficient in groups.items():
        if coefficient == 1:
            eligible[angle_id].add(mask)

    selected: list[tuple[str, tuple[int, int, int]]] = []
    used: set[tuple[int, str]] = set()
    for angle_id in sorted(eligible):
        for triple in dependent_triples(eligible[angle_id]):
            if any((mask, angle_id) in used for mask in triple):
                continue
            selected.append((angle_id, triple))
            used.update((mask, angle_id) for mask in triple)

    required_workspace = 3 if selected else 0
    if (
        constraints.workspace_budget is not None
        and required_workspace > constraints.workspace_budget
    ):
        trace.append(
            {
                "action": "rewrite_skipped",
                "reason": f"detected triples require {required_workspace} clean qubits",
            }
        )
        selected = []
        used.clear()
        required_workspace = 0

    operations: list[Operation] = []
    qa, qb, qor = program.qubit_count, program.qubit_count + 1, program.qubit_count + 2
    for angle_id, triple in selected:
        first, second, third = triple
        append_parity_into(operations, first, qa)
        append_parity_into(operations, second, qb)
        operations.append(Operation("and_compute", (qa, qb, qor)))
        operations.append(Operation("cx", (qa, qor)))
        operations.append(Operation("cx", (qb, qor)))
        operations.append(Operation("phase", (qor,), angle_id, 2))
        operations.append(Operation("cx", (qb, qor)))
        operations.append(Operation("cx", (qa, qor)))
        operations.append(Operation("and_uncompute", (qa, qb, qor)))
        append_parity_into(operations, second, qb)
        append_parity_into(operations, first, qa)
        trace.append(
            {
                "action": "dependent_triple_to_or",
                "angle_id": angle_id,
                "masks": [first, second, third],
                "identity": "a + b + (a XOR b) = 2(a OR b)",
            }
        )

    for (mask, angle_id), coefficient in sorted(groups.items()):
        if (mask, angle_id) not in used:
            append_parity_phase(operations, mask, angle_id, coefficient)

    if not selected:
        trace.append(
            {
                "action": "no_rewrite",
                "reason": "no disjoint equal-angle unit-coefficient dependent triple",
            }
        )
    return Candidate(
        method="dependent_triples",
        version="0.1",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=required_workspace,
        global_phase=global_phase,
        model_profile=constraints.model_profile,
        parameters={
            "workspace_budget": constraints.workspace_budget,
            "selection": "lexicographic_disjoint_greedy",
            "matched_triples": len(selected),
        },
        transformation_trace=trace,
        proof_obligations=[
            "for each match, the three masks XOR to zero",
            "OR workspace and predicate workspaces return to zero",
        ],
        accounting_status=(
            "emitted"
            if constraints.model_profile == "unitary_clifford_t" or not selected
            else "estimated_macro"
        ),
    )
