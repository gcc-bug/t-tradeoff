from __future__ import annotations

from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from ..preprocessing import PREPROCESSING_VERSION, CompatibleGroup, preprocess
from .arithmetic import (
    hamming_weight_compute,
    hwp_adder_workspace,
    hwp_compressor_count,
    invert_classical_operations,
)
from .common import (
    CompilationConstraints,
    append_direct_term,
    append_parity_into,
    batch_sizes,
    chunks,
    max_batch_size,
)


def _emit_adder_batch(
    program: PhaseProgram,
    group: CompatibleGroup,
    batch: list,
) -> tuple[list[Operation], int, dict]:
    size = len(batch)
    if size < 2:
        operations: list[Operation] = []
        append_direct_term(operations, batch[0])
        return operations, 0, {
            "action": "direct_singleton_fallback",
            "group_id": group.id,
            "term_ids": [batch[0].id],
        }

    parity = tuple(range(program.qubit_count, program.qubit_count + size))
    carry_count = hwp_compressor_count(size)
    carries = tuple(
        range(
            program.qubit_count + size,
            program.qubit_count + size + carry_count,
        )
    )
    operations = []
    for term, target in zip(batch, parity, strict=True):
        append_parity_into(operations, term.mask, target)
    arithmetic, layout = hamming_weight_compute(parity, carries)
    operations.extend(arithmetic)
    for bit, target in enumerate(layout.output_qubits):
        operations.append(
            Operation(
                "phase",
                (target,),
                group.angle_id,
                group.coefficient * (1 << bit),
            )
        )
    operations.extend(invert_classical_operations(arithmetic))
    for term, target in reversed(list(zip(batch, parity, strict=True))):
        append_parity_into(operations, term.mask, target)
    return operations, hwp_adder_workspace(size), {
        "action": "hwp_adder_unitary_batch",
        "group_id": group.id,
        "block_id": group.block_id,
        "angle_id": group.angle_id,
        "coefficient": group.coefficient,
        "term_ids": [term.id for term in batch],
        "size": size,
        "parity_qubits": list(parity),
        "weight_qubits": list(layout.output_qubits),
        "retained_garbage_qubits": list(layout.garbage_qubits),
        "carry_qubits": list(layout.carry_qubits),
        "stage_widths": list(layout.stage_widths),
        "arithmetic": "staged_3_to_2_and_2_to_2_compressors",
        "forward_toffolis": carry_count,
        "unitary_cleanup_toffolis": carry_count,
    }


def compile_hwp_adder_unitary(
    program: PhaseProgram,
    constraints: CompilationConstraints,
    *,
    batch_limit: int | None = None,
) -> Candidate:
    """Compile ordinary HWP using an emitted linear-size compressor network."""
    if constraints.model_profile != "unitary_clifford_t":
        return Candidate.infeasible(
            "hwp_adder_unitary",
            program,
            "the audited adder HWP is a unitary adaptation; measured cleanup is not emitted",
            model_profile=constraints.model_profile,
        )
    normalized = preprocess(program)
    limit = batch_limit or constraints.hwp_search_cap
    operations: list[Operation] = []
    trace = list(normalized.trace)
    peak_workspace = 0
    collective_batches = 0

    for group in normalized.groups:
        terms = list(group.terms)
        capacity = max_batch_size(
            min(len(terms), limit),
            constraints.workspace_budget,
            hwp_adder_workspace,
        )
        if len(terms) < 2 or capacity < 2:
            for term in terms:
                append_direct_term(operations, term)
            trace.append(
                {
                    "action": "direct_group_fallback",
                    "group_id": group.id,
                    "reason": "singleton group or workspace cannot fit an adder batch",
                    "term_ids": [term.id for term in terms],
                }
            )
            continue
        sizes = batch_sizes(len(terms), capacity, "balanced")
        for batch in chunks(terms, sizes):
            batch_operations, workspace, batch_trace = _emit_adder_batch(
                program, group, batch
            )
            operations.extend(batch_operations)
            peak_workspace = max(peak_workspace, workspace)
            collective_batches += int(len(batch) > 1)
            trace.append(batch_trace)

    return Candidate(
        method="hwp_adder_unitary",
        version="0.3",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=peak_workspace,
        global_phase=normalized.global_phase,
        model_profile=constraints.model_profile,
        parameters={
            "workspace_budget": constraints.workspace_budget,
            "batch_limit": limit,
            "batch_policy": "balanced_for_fixed_limit",
            "collective_batches": collective_batches,
            "workspace_scope": "parity_materialization_plus_clean_carries",
            "cleanup_model": "unitary_reverse_of_compute",
            "source": "Kivlichan et al. arXiv:1902.10673v4 Appendix A.1",
        },
        transformation_trace=trace,
        proof_obligations=[
            "compressor truth tables preserve weighted sums",
            "weight-bit phases equal the sum of equal-angle predicates",
            "reversed arithmetic and parity preparation restore every workspace qubit",
        ],
        accounting_status="emitted",
        implementation_family="ordinary_hwp",
        variant=f"adder_compressor_unitary_cap_{limit}",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )


def compile_hwp_adder_unitary_alternatives(
    program: PhaseProgram, constraints: CompilationConstraints
) -> list[Candidate]:
    normalized = preprocess(program)
    largest_group = max((len(group.terms) for group in normalized.groups), default=1)
    max_limit = min(largest_group, constraints.hwp_search_cap)
    return [
        compile_hwp_adder_unitary(program, constraints, batch_limit=limit)
        for limit in range(1, max_limit + 1)
    ]
