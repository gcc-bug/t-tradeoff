from __future__ import annotations

from dataclasses import replace

from ..baselines.common import (
    CompilationConstraints,
    append_direct_term,
    append_parity_into,
)
from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from ..preprocessing import PREPROCESSING_VERSION, CompatibleGroup, preprocess
from ..profiles import dependent_triples


def _select_disjoint_triples(
    groups: tuple[CompatibleGroup, ...],
) -> tuple[list[tuple[CompatibleGroup, tuple[int, int, int]]], set[str]]:
    selected: list[tuple[CompatibleGroup, tuple[int, int, int]]] = []
    used_terms: set[str] = set()
    for group in groups:
        by_mask = {term.mask: term for term in group.terms}
        for triple in dependent_triples(by_mask):
            terms = [by_mask[mask] for mask in triple]
            if any(term.id in used_terms for term in terms):
                continue
            selected.append((group, triple))
            used_terms.update(term.id for term in terms)
    return selected, used_terms


def _emit_or_rewrite(
    program: PhaseProgram,
    selected: list[tuple[CompatibleGroup, tuple[int, int, int]]],
) -> tuple[list[Operation], list[dict]]:
    operations: list[Operation] = []
    trace: list[dict] = []
    qa, qb, qor = (
        program.qubit_count,
        program.qubit_count + 1,
        program.qubit_count + 2,
    )
    for group, triple in selected:
        first, second, third = triple
        append_parity_into(operations, first, qa)
        append_parity_into(operations, second, qb)
        operations.append(Operation("toffoli", (qa, qb, qor)))
        operations.append(Operation("cx", (qa, qor)))
        operations.append(Operation("cx", (qb, qor)))
        operations.append(
            Operation(
                "phase",
                (qor,),
                group.angle_id,
                2 * group.coefficient,
            )
        )
        operations.append(Operation("cx", (qb, qor)))
        operations.append(Operation("cx", (qa, qor)))
        operations.append(Operation("toffoli", (qa, qb, qor)))
        append_parity_into(operations, second, qb)
        append_parity_into(operations, first, qa)
        trace.append(
            {
                "action": "dependent_triple_to_or",
                "group_id": group.id,
                "block_id": group.block_id,
                "angle_id": group.angle_id,
                "coefficient": group.coefficient,
                "masks": [first, second, third],
                "identity": "a + b + (a XOR b) = 2(a OR b)",
            }
        )
    return operations, trace


def compile_dependent_triples_raw(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    normalized = preprocess(program)
    selected, used_terms = _select_disjoint_triples(normalized.groups)
    if selected and constraints.workspace_budget is not None and constraints.workspace_budget < 3:
        return Candidate(
            method="dependent_triples_raw",
            version="0.2",
            program=program,
            status="infeasible",
            model_profile=constraints.model_profile,
            failure_reason="raw triple rewrite requires three clean work qubits",
            implementation_family="dependent_triples",
            variant="raw_lexicographic_disjoint",
            objective=constraints.objective,
            preprocessing_version=PREPROCESSING_VERSION,
            parameters={
                "workspace_budget": constraints.workspace_budget,
                "detected_triples": len(selected),
                "used_rewrite": False,
            },
        )

    operations, rewrite_trace = _emit_or_rewrite(program, selected)
    for term in normalized.terms:
        if term.id not in used_terms:
            append_direct_term(operations, term)
    trace = list(normalized.trace) + rewrite_trace
    if not selected:
        trace.append(
            {
                "action": "no_rewrite",
                "reason": "no disjoint compatible dependent triple",
            }
        )
    return Candidate(
        method="dependent_triples_raw",
        version="0.2",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=3 if selected else 0,
        global_phase=normalized.global_phase,
        model_profile=constraints.model_profile,
        parameters={
            "workspace_budget": constraints.workspace_budget,
            "selection": "lexicographic_disjoint_greedy",
            "matched_triples": len(selected),
            "used_rewrite": bool(selected),
        },
        transformation_trace=trace,
        proof_obligations=[
            "each selected triple is within one block and compatible group",
            "for each match, the three masks XOR to zero",
            "OR and predicate workspaces return to zero",
        ],
        accounting_status=(
            "emitted"
            if constraints.model_profile == "unitary_clifford_t" or not selected
            else "unverified_estimate"
        ),
        implementation_family="dependent_triples",
        variant="raw_lexicographic_disjoint",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )


def compile_hwp_dependency_simplified(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    """Same triple groups, interpreted as simplified HWP output bits."""
    raw = compile_dependent_triples_raw(program, constraints)
    if raw.status != "success":
        return replace(
            raw,
            method="hwp_dependency_simplified",
            implementation_family="ordinary_hwp",
            variant="triple_weight_bits_simplified",
        )
    trace = list(raw.transformation_trace)
    for item in trace:
        if item.get("action") == "dependent_triple_to_or":
            item["action"] = "hwp_weight_bits_simplified"
            item["certificate"] = {
                "weight_bit_0": "constant 0",
                "weight_bit_1": "a OR b",
                "truth_table": [0, 2, 2, 2],
            }
    return replace(
        raw,
        method="hwp_dependency_simplified",
        implementation_family="ordinary_hwp",
        variant="triple_weight_bits_simplified",
        transformation_trace=trace,
        proof_obligations=list(raw.proof_obligations)
        + ["bounded truth table proves the simplified HWP weight bits"],
    )


# Compatibility entry point for historical tests and external callers.
compile_dependent_triples = compile_dependent_triples_raw
