from __future__ import annotations

from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from .common import (
    CompilationConstraints,
    append_parity_into,
    batch_sizes,
    chunks,
    hwp_workspace,
    max_batch_size,
    validate_equal_unit_terms,
)


def compile_hwp(program: PhaseProgram, constraints: CompilationConstraints) -> Candidate:
    reason = validate_equal_unit_terms(program)
    if reason:
        return Candidate.infeasible(
            "hwp", program, reason, model_profile=constraints.model_profile
        )
    operations: list[Operation] = []
    trace: list[dict] = []
    peak = 0
    for block in program.blocks:
        terms = [term for term in block.terms if term.mask]
        capacity = max_batch_size(len(terms), constraints.workspace_budget, hwp_workspace)
        if terms and capacity == 0:
            return Candidate.infeasible(
                "hwp",
                program,
                "workspace budget cannot materialize one parity predicate",
                model_profile=constraints.model_profile,
            )
        sizes = batch_sizes(len(terms), capacity, constraints.batch_policy) if terms else []
        for batch_index, batch in enumerate(chunks(terms, sizes)):
            size = len(batch)
            peak = max(peak, hwp_workspace(size))
            parity_qubits = list(range(program.qubit_count, program.qubit_count + size))
            for term, target in zip(batch, parity_qubits, strict=True):
                append_parity_into(operations, term.mask, target)
            if size == 1:
                operations.append(Operation("phase", (parity_qubits[0],), batch[0].angle_id, 1))
            else:
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
                    "source": "Kivlichan et al. Appendix A; conservative scratch bound",
                }
                operations.append(
                    Operation("hwp_compute", tuple(parity_qubits + scratch), payload=payload)
                )
                for bit, target in enumerate(weight_qubits):
                    operations.append(Operation("phase", (target,), batch[0].angle_id, 1 << bit))
                operations.append(
                    Operation("hwp_uncompute", tuple(parity_qubits + scratch), payload=payload)
                )
            for term, target in reversed(list(zip(batch, parity_qubits, strict=True))):
                append_parity_into(operations, term.mask, target)
            trace.append(
                {
                    "action": "ordinary_hwp_batch",
                    "block": block.id,
                    "batch": batch_index,
                    "term_ids": [term.id for term in batch],
                    "size": size,
                }
            )
    return Candidate(
        method="hwp",
        version="0.1",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=peak,
        model_profile=constraints.model_profile,
        parameters={
            "workspace_budget": constraints.workspace_budget,
            "batch_policy": constraints.batch_policy,
        },
        transformation_trace=trace,
        proof_obligations=[
            "published Hamming-weight adder macro implements and uncomputes binary weight",
            "parity materialization registers return to zero",
        ],
        accounting_status="estimated_macro",
    )
