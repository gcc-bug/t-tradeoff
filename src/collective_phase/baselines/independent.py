from __future__ import annotations

from ..circuit import Candidate
from ..ir import PhaseProgram
from .common import CompilationConstraints, append_parity_phase


def compile_independent(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    groups, global_phase, trace = program.normalized_groups()
    operations = []
    for (mask, angle_id), coefficient in sorted(groups.items()):
        append_parity_phase(operations, mask, angle_id, coefficient)
    trace.append(
        {
            "action": "combine_identical_phase_functions",
            "input_terms": len(program.terms),
            "output_rotations": len(groups),
        }
    )
    return Candidate(
        method="independent",
        version="0.1",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=0,
        global_phase=global_phase,
        model_profile=constraints.model_profile,
        parameters={"workspace_budget": constraints.workspace_budget},
        transformation_trace=trace,
        proof_obligations=["CNOT parity compute/uncompute restores the data register"],
    )

