from __future__ import annotations

from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from ..preprocessing import PREPROCESSING_VERSION, CompatibleGroup, preprocess
from .arithmetic import (
    hamming_weight_compute,
    hwp_adder_workspace,
    hwp_compressor_count,
    hwp_in_place_workspace,
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


def _is_in_place_group(program: PhaseProgram, group: CompatibleGroup) -> bool:
    """Recognize only distinct, positive, unweighted data-wire predicates."""
    source_terms = {term.id: term for term in program.terms}
    if group.coefficient != 1:
        return False
    masks = [term.mask for term in group.terms]
    if len(set(masks)) != len(masks):
        return False
    for term in group.terms:
        if term.mask <= 0 or term.mask & (term.mask - 1):
            return False
        if len(term.source_term_ids) != 1:
            return False
        source = source_terms[term.source_term_ids[0]]
        if source.offset or source.coefficient != 1:
            return False
    return True


def _emit_adder_batch(
    program: PhaseProgram,
    group: CompatibleGroup,
    batch: list,
    *,
    layout: str,
    ordering: str = "staged",
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

    carry_count = hwp_compressor_count(size)
    layout_name = layout
    if layout_name == "in_place_inputs":
        parity = tuple(term.mask.bit_length() - 1 for term in batch)
        workspace = hwp_in_place_workspace(size)
        carries = tuple(
            range(program.qubit_count, program.qubit_count + carry_count)
        )
        operations: list[Operation] = []
    elif layout_name == "copied_parities":
        parity = tuple(range(program.qubit_count, program.qubit_count + size))
        workspace = hwp_adder_workspace(size)
        carries = tuple(
            range(
                program.qubit_count + size,
                program.qubit_count + size + carry_count,
            )
        )
        operations = []
        for term, target in zip(batch, parity, strict=True):
            append_parity_into(operations, term.mask, target)
    else:
        raise ValueError(f"unsupported HWP layout {layout_name!r}")
    arithmetic, weight_layout = hamming_weight_compute(parity, carries, ordering=ordering)
    operations.extend(arithmetic)
    for bit, target in enumerate(weight_layout.output_qubits):
        operations.append(
            Operation(
                "phase",
                (target,),
                group.angle_id,
                group.coefficient * (1 << bit),
            )
        )
    operations.extend(invert_classical_operations(arithmetic))
    if layout_name == "copied_parities":
        for term, target in reversed(list(zip(batch, parity, strict=True))):
            append_parity_into(operations, term.mask, target)
    return operations, workspace, {
        "action": "hwp_adder_unitary_batch",
        "group_id": group.id,
        "block_id": group.block_id,
        "angle_id": group.angle_id,
        "coefficient": group.coefficient,
        "term_ids": [term.id for term in batch],
        "size": size,
        "layout": layout_name,
        "ordering": ordering,
        "data_restored": True,
        "parity_qubits": list(parity),
        "weight_qubits": list(weight_layout.output_qubits),
        "retained_garbage_qubits": list(weight_layout.garbage_qubits),
        "carry_qubits": list(weight_layout.carry_qubits),
        "stage_widths": list(weight_layout.stage_widths),
        "arithmetic": "staged_3_to_2_and_2_to_2_compressors",
        "forward_toffolis": carry_count,
        "unitary_cleanup_toffolis": carry_count,
    }


def compile_hwp_adder_unitary(
    program: PhaseProgram,
    constraints: CompilationConstraints,
    *,
    batch_limit: int | None = None,
    layout: str = "auto",
    ordering: str = "staged",
) -> Candidate:
    """Compile ordinary HWP using an emitted linear-size compressor network."""
    if constraints.model_profile != "unitary_clifford_t":
        return Candidate.infeasible(
            "hwp_adder_unitary",
            program,
            "the audited adder HWP is a unitary adaptation; measured cleanup is not emitted",
            model_profile=constraints.model_profile,
        )
    if ordering not in {"staged", "readiness"}:
        raise ValueError(f"unsupported arithmetic ordering {ordering!r}")
    if layout not in {"auto", "copied_parities", "in_place_inputs"}:
        raise ValueError(f"unsupported HWP layout {layout!r}")
    normalized = preprocess(program)
    limit = batch_limit or constraints.hwp_search_cap
    operations: list[Operation] = []
    trace = list(normalized.trace)
    peak_workspace = 0
    collective_batches = 0

    for group in normalized.groups:
        terms = list(group.terms)
        in_place = _is_in_place_group(program, group)
        if layout == "in_place_inputs" and not in_place:
            for term in terms:
                append_direct_term(operations, term)
            trace.append(
                {
                    "action": "direct_group_fallback",
                    "group_id": group.id,
                    "reason": "in-place HWP requires distinct positive singleton predicates",
                    "term_ids": [term.id for term in terms],
                }
            )
            continue
        group_layout = (
            "in_place_inputs"
            if in_place and layout in {"auto", "in_place_inputs"}
            else "copied_parities"
        )
        workspace_for = (
            hwp_in_place_workspace
            if group_layout == "in_place_inputs"
            else hwp_adder_workspace
        )
        capacity = max_batch_size(
            min(len(terms), limit),
            constraints.workspace_budget,
            workspace_for,
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
                program, group, batch, layout=group_layout, ordering=ordering
            )
            operations.extend(batch_operations)
            peak_workspace = max(peak_workspace, workspace)
            collective_batches += int(len(batch) > 1)
            trace.append(batch_trace)

    return Candidate(
        method="hwp_adder_unitary",
        version="0.4",
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
            "layout": layout,
            "ordering": ordering,
            "collective_batches": collective_batches,
            "workspace_scope": "clean_carries_with_in_place_data_when_applicable",
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
        variant=f"adder_compressor_unitary_{layout}_cap_{limit}",
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
