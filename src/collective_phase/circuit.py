from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ir import PhaseProgram


@dataclass(frozen=True)
class Operation:
    kind: str
    qubits: tuple[int, ...] = ()
    angle_id: str | None = None
    multiplier: int = 1
    payload: dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind, "qubits": list(self.qubits)}
        if self.angle_id is not None:
            result["angle_id"] = self.angle_id
            result["multiplier"] = self.multiplier
        if self.payload:
            result["payload"] = self.payload
        return result


@dataclass
class Candidate:
    method: str
    version: str
    program: PhaseProgram
    status: str
    operations: list[Operation] = field(default_factory=list)
    workspace_qubits: int = 0
    global_phase: float = 0.0
    model_profile: str = "unitary_clifford_t"
    parameters: dict[str, Any] = field(default_factory=dict)
    transformation_trace: list[dict[str, Any]] = field(default_factory=list)
    required_resource_states: list[dict[str, Any]] = field(default_factory=list)
    proof_obligations: list[str] = field(default_factory=list)
    accounting_status: str = "emitted"
    failure_reason: str | None = None

    @classmethod
    def infeasible(
        cls,
        method: str,
        program: PhaseProgram,
        reason: str,
        *,
        model_profile: str,
    ) -> "Candidate":
        return cls(
            method=method,
            version="0.1",
            program=program,
            status="infeasible",
            model_profile=model_profile,
            failure_reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "method": self.method,
            "version": self.version,
            "program_id": self.program.id,
            "status": self.status,
            "model_profile": self.model_profile,
            "workspace_qubits": self.workspace_qubits,
            "global_phase": self.global_phase,
            "parameters": self.parameters,
            "operations": [operation.to_dict() for operation in self.operations],
            "transformation_trace": self.transformation_trace,
            "required_resource_states": self.required_resource_states,
            "proof_obligations": self.proof_obligations,
            "accounting_status": self.accounting_status,
            "failure_reason": self.failure_reason,
        }


def data_support(mask: int) -> list[int]:
    return [index for index in range(mask.bit_length()) if (mask >> index) & 1]

