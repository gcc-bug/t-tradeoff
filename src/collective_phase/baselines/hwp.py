from __future__ import annotations

from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from ..preprocessing import PREPROCESSING_VERSION, CompatibleGroup, preprocess
from ..profiles import dependent_triples
from .arithmetic import (
    ANF_REFERENCE_MAX_INPUTS,
    emitted_hwp_workspace,
    hamming_weight_compute,
    hwp_adder_workspace,
    hwp_compressor_count,
    invert_classical_operations,
    population_count_compute,
    population_count_scratch,
    population_count_width,
)
from .common import (
    CompilationConstraints,
    append_direct_term,
    append_parity_into,
    batch_sizes,
    chunks,
    hwp_workspace,
    max_batch_size,
)


def _emit_reference_batch(
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

    width = population_count_width(size)
    scratch_width = population_count_scratch(size)
    parity = tuple(range(program.qubit_count, program.qubit_count + size))
    weight = tuple(
        range(program.qubit_count + size, program.qubit_count + size + width)
    )
    scratch = tuple(
        range(
            program.qubit_count + size + width,
            program.qubit_count + size + width + scratch_width,
        )
    )
    operations = []
    for term, target in zip(batch, parity, strict=True):
        append_parity_into(operations, term.mask, target)
    arithmetic = population_count_compute(parity, weight, scratch)
    operations.extend(arithmetic)
    for bit, target in enumerate(weight):
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
    return operations, emitted_hwp_workspace(size), {
        "action": "emitted_hwp_batch",
        "group_id": group.id,
        "block_id": group.block_id,
        "angle_id": group.angle_id,
        "coefficient": group.coefficient,
        "term_ids": [term.id for term in batch],
        "size": size,
        "weight_width": width,
        "scratch_width": scratch_width,
        "arithmetic": "out_of_place_anf_population_count",
    }


def compile_hwp_emitted(
    program: PhaseProgram,
    constraints: CompilationConstraints,
    *,
    batch_limit: int | None = None,
) -> Candidate:
    if constraints.model_profile != "unitary_clifford_t":
        return Candidate.infeasible(
            "hwp_emitted",
            program,
            "the emitted HWP reference is currently unitary-only",
            model_profile=constraints.model_profile,
        )
    normalized = preprocess(program)
    limit = min(
        batch_limit or constraints.hwp_search_cap,
        ANF_REFERENCE_MAX_INPUTS,
    )
    operations: list[Operation] = []
    trace = list(normalized.trace)
    peak_workspace = 0
    collective_batches = 0

    for group in normalized.groups:
        terms = list(group.terms)
        if len(terms) < 2 or limit < 2:
            for term in terms:
                append_direct_term(operations, term)
            trace.append(
                {
                    "action": "direct_group_fallback",
                    "group_id": group.id,
                    "reason": "singleton group or batch limit one",
                    "term_ids": [term.id for term in terms],
                }
            )
            continue
        capacity = max_batch_size(
            min(len(terms), limit),
            constraints.workspace_budget,
            emitted_hwp_workspace,
        )
        if capacity < 2:
            for term in terms:
                append_direct_term(operations, term)
            trace.append(
                {
                    "action": "direct_group_fallback",
                    "group_id": group.id,
                    "reason": "workspace cannot fit a collective emitted batch",
                    "term_ids": [term.id for term in terms],
                }
            )
            continue
        sizes = batch_sizes(len(terms), capacity, "balanced")
        for batch in chunks(terms, sizes):
            batch_operations, workspace, batch_trace = _emit_reference_batch(
                program, group, batch
            )
            operations.extend(batch_operations)
            peak_workspace = max(peak_workspace, workspace)
            collective_batches += int(len(batch) > 1)
            trace.append(batch_trace)

    return Candidate(
        method="hwp_emitted",
        version="0.2",
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
            "workspace_scope": "implementation_upper_bound",
        },
        transformation_trace=trace,
        proof_obligations=[
            "ANF population-count outputs equal the binary Hamming weight",
            "all arithmetic, parity, and scratch registers return to zero",
        ],
        accounting_status="emitted",
        implementation_family="ordinary_hwp",
        variant=f"reference_anf_out_of_place_cap_{limit}",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )


def compile_hwp_emitted_alternatives(
    program: PhaseProgram, constraints: CompilationConstraints
) -> list[Candidate]:
    normalized = preprocess(program)
    largest_group = max((len(group.terms) for group in normalized.groups), default=1)
    max_limit = min(
        largest_group,
        constraints.hwp_search_cap,
        ANF_REFERENCE_MAX_INPUTS,
    )
    candidates: list[Candidate] = []
    for limit in range(1, max_limit + 1):
        candidates.append(
            compile_hwp_emitted(program, constraints, batch_limit=limit)
        )
    return candidates


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


def compile_hwp_emitted_triple_grouped(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    """Apply generic emitted HWP to the raw candidate's exact triple groups."""
    if constraints.model_profile != "unitary_clifford_t":
        return Candidate.infeasible(
            "hwp_emitted_triple_grouped",
            program,
            "the emitted HWP reference is currently unitary-only",
            model_profile=constraints.model_profile,
        )
    normalized = preprocess(program)
    operations: list[Operation] = []
    trace = list(normalized.trace)
    used_terms: set[str] = set()
    peak_workspace = 0
    grouped_triples = 0
    for group in normalized.groups:
        by_mask = {term.mask: term for term in group.terms}
        for triple in dependent_triples(by_mask):
            batch = [by_mask[mask] for mask in triple]
            if any(term.id in used_terms for term in batch):
                continue
            if (
                constraints.workspace_budget is not None
                and emitted_hwp_workspace(3) > constraints.workspace_budget
            ):
                continue
            batch_operations, workspace, batch_trace = _emit_reference_batch(
                program, group, batch
            )
            operations.extend(batch_operations)
            peak_workspace = max(peak_workspace, workspace)
            used_terms.update(term.id for term in batch)
            grouped_triples += 1
            batch_trace["action"] = "emitted_hwp_candidate_triple_group"
            batch_trace["masks"] = list(triple)
            trace.append(batch_trace)
    for term in normalized.terms:
        if term.id not in used_terms:
            append_direct_term(operations, term)
    trace.append(
        {
            "action": "candidate_triple_grouping_ablation",
            "grouped_triples": grouped_triples,
            "fallback_terms": len(normalized.terms) - len(used_terms),
        }
    )
    return Candidate(
        method="hwp_emitted_triple_grouped",
        version="0.2",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=peak_workspace,
        global_phase=normalized.global_phase,
        model_profile=constraints.model_profile,
        parameters={
            "workspace_budget": constraints.workspace_budget,
            "grouping": "raw_candidate_lexicographic_disjoint_triples",
            "grouped_triples": grouped_triples,
            "workspace_scope": "implementation_upper_bound",
        },
        transformation_trace=trace,
        proof_obligations=[
            "each emitted batch uses the raw candidate's exact triple grouping",
            "generic ANF population-count arithmetic returns all work qubits to zero",
        ],
        accounting_status="emitted",
        implementation_family="ordinary_hwp",
        variant="reference_anf_candidate_triple_groups",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )


def compile_hwp_macro_legacy(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    """Preserved v1 estimate, now fed by canonical preprocessing."""
    normalized = preprocess(program)
    operations: list[Operation] = []
    trace = list(normalized.trace)
    peak = 0
    collective_batches = 0
    for group in normalized.groups:
        terms = list(group.terms)
        capacity = max_batch_size(
            len(terms), constraints.workspace_budget, hwp_workspace
        )
        if capacity < 2:
            for term in terms:
                append_direct_term(operations, term)
            trace.append(
                {
                    "action": "legacy_direct_fallback",
                    "group_id": group.id,
                    "term_ids": [term.id for term in terms],
                }
            )
            continue
        sizes = batch_sizes(len(terms), capacity, constraints.batch_policy)
        for batch_index, batch in enumerate(chunks(terms, sizes)):
            size = len(batch)
            if size == 1:
                append_direct_term(operations, batch[0])
                continue
            collective_batches += 1
            peak = max(peak, hwp_workspace(size))
            parity_qubits = list(
                range(program.qubit_count, program.qubit_count + size)
            )
            for term, target in zip(batch, parity_qubits, strict=True):
                append_parity_into(operations, term.mask, target)
            weight_width = size.bit_length()
            scratch_width = max(size - 1, weight_width)
            scratch = list(
                range(
                    program.qubit_count + size,
                    program.qubit_count + size + scratch_width,
                )
            )
            weight_qubits = scratch[:weight_width]
            payload = {
                "control_count": size,
                "weight_count": weight_width,
                "batch_size": size,
                "source": "legacy Kivlichan Appendix A macro estimate",
            }
            operations.append(
                Operation(
                    "hwp_compute", tuple(parity_qubits + scratch), payload=payload
                )
            )
            for bit, target in enumerate(weight_qubits):
                operations.append(
                    Operation(
                        "phase",
                        (target,),
                        group.angle_id,
                        group.coefficient * (1 << bit),
                    )
                )
            operations.append(
                Operation(
                    "hwp_uncompute", tuple(parity_qubits + scratch), payload=payload
                )
            )
            for term, target in reversed(
                list(zip(batch, parity_qubits, strict=True))
            ):
                append_parity_into(operations, term.mask, target)
            trace.append(
                {
                    "action": "legacy_hwp_macro_batch",
                    "group_id": group.id,
                    "batch": batch_index,
                    "term_ids": [term.id for term in batch],
                    "size": size,
                }
            )
    return Candidate(
        method="hwp_macro_legacy",
        version="0.2",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=peak,
        global_phase=normalized.global_phase,
        model_profile=constraints.model_profile,
        parameters={
            "workspace_budget": constraints.workspace_budget,
            "batch_policy": constraints.batch_policy,
            "collective_batches": collective_batches,
        },
        transformation_trace=trace,
        proof_obligations=["legacy macro semantics only"],
        accounting_status="estimated_macro" if collective_batches else "emitted",
        implementation_family="ordinary_hwp",
        variant="legacy_formula_macro",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )


# Compatibility entry point. New configurations must use hwp_macro_legacy or
# hwp_emitted explicitly so the circuit identity cannot change silently.
compile_hwp = compile_hwp_macro_legacy
