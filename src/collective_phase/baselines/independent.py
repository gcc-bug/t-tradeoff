from __future__ import annotations

from ..circuit import Candidate
from ..ir import PhaseProgram
from ..preprocessing import PREPROCESSING_VERSION, preprocess
from .common import CompilationConstraints, append_direct_term


def compile_independent(
    program: PhaseProgram, constraints: CompilationConstraints
) -> Candidate:
    normalized = preprocess(program)
    operations = []
    for term in normalized.terms:
        append_direct_term(operations, term)
    trace = list(normalized.trace)
    trace.append(
        {
            "action": "combine_identical_phase_functions",
            "input_terms": len(program.terms),
            "output_rotations": len(normalized.terms),
        }
    )
    return Candidate(
        method="independent",
        version="0.1",
        program=program,
        status="success",
        operations=operations,
        workspace_qubits=0,
        global_phase=normalized.global_phase,
        model_profile=constraints.model_profile,
        parameters={"workspace_budget": constraints.workspace_budget},
        transformation_trace=trace,
        proof_obligations=["CNOT parity compute/uncompute restores the data register"],
        implementation_family="direct",
        variant="normalized_independent",
        objective=constraints.objective,
        preprocessing_version=PREPROCESSING_VERSION,
    )
