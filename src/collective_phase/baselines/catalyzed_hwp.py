from __future__ import annotations

import math

from ..circuit import Candidate, Operation
from ..ir import PhaseProgram
from ..preprocessing import PREPROCESSING_VERSION, preprocess
from .common import (
    CompilationConstraints,
    append_parity_into,
    batch_sizes,
    catalyst_workspace,
    chunks,
    max_batch_size,
)


def compile_catalyzed_hwp(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    normalized = preprocess(program)
    operations: list[Operation] = []
    trace: list[dict] = list(normalized.trace)
    resource_states: dict[tuple[str, int, int], dict] = {}
    peak = 0
    for group in normalized.groups:
        terms = list(group.terms)
        capacity = max_batch_size(
            len(terms), constraints.workspace_budget, catalyst_workspace
        )
        if terms and capacity == 0:
            return Candidate.infeasible(
                "catalyzed_hwp_unverified",
                program,
                "workspace budget cannot materialize one parity predicate",
                model_profile=constraints.model_profile,
            )
        sizes = (
            batch_sizes(
                len(terms), capacity, constraints.batch_policy, catalyzed=True
            )
            if terms
            else []
        )
        for batch_index, batch in enumerate(chunks(terms, sizes)):
            size = len(batch)
            peak = max(peak, catalyst_workspace(size))
            parity_qubits = list(range(program.qubit_count, program.qubit_count + size))
            for term, target in zip(batch, parity_qubits, strict=True):
                append_parity_into(operations, term.mask, target)
            if size == 1:
                operations.append(
                    Operation(
                        "phase",
                        (parity_qubits[0],),
                        group.angle_id,
                        group.coefficient,
                    )
                )
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
                    "hwp_adders": size - size.bit_count(),
                }
                operations.append(
                    Operation("hwp_compute", tuple(parity_qubits + scratch), payload=payload)
                )
                gradient_toffolis = math.ceil(math.log2(size)) + 1
                operations.append(
                    Operation(
                        "phase_gradient",
                        tuple(weight_qubits),
                        group.angle_id,
                        group.coefficient,
                        {
                            "batch_size": size,
                            "gradient_toffolis": gradient_toffolis,
                            "catalyst_width": weight_width,
                            "reuse_count": constraints.catalyst_reuse_count,
                            "source": "Kan-Symons arXiv:2411.02160v2, HWP section",
                        },
                    )
                )
                operations.append(
                    Operation("hwp_uncompute", tuple(parity_qubits + scratch), payload=payload)
                )
                resource_states[
                    (group.angle_id, group.coefficient, weight_width)
                ] = {
                    "kind": "phase_gradient_catalyst",
                    "angle_id": group.angle_id,
                    "multipliers": [
                        group.coefficient * (1 << bit)
                        for bit in range(weight_width)
                    ],
                    "qubits": weight_width,
                    "preparation": "Rz(2^i theta)|+> for each catalyst qubit",
                    "returned_ideally": True,
                }
            for term, target in reversed(list(zip(batch, parity_qubits, strict=True))):
                append_parity_into(operations, term.mask, target)
            trace.append(
                {
                    "action": "catalyzed_hwp_batch",
                    "block_id": group.block_id,
                    "group_id": group.id,
                    "batch": batch_index,
                    "term_ids": [term.id for term in batch],
                    "size": size,
                }
            )
    return Candidate(
        method="catalyzed_hwp_unverified",
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
            "reuse_count": constraints.catalyst_reuse_count,
        },
        transformation_trace=trace,
        required_resource_states=list(resource_states.values()),
        proof_obligations=[
            "phase-gradient catalyst is supplied and returned ideally",
            "catalyst approximation error is charged once, not reset per reuse",
            "published Hamming-weight and generalized phase-gradient macros apply",
        ],
        accounting_status="unverified_estimate",
        implementation_family="catalyzed_hwp",
        variant="legacy_formula_macro_unverified",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )
