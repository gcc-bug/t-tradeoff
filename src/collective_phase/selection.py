from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .circuit import Candidate
from .lowering import LoweredCircuit, RotationSynthesizer, lower_candidate
from .resources import ResourceRecord, estimate_resources
from .verification import (
    LoweredVerificationResult,
    VerificationResult,
    verify_candidate,
    verify_lowered_circuit,
)


@dataclass
class EvaluatedAlternative:
    label: str
    candidate: Candidate
    ideal_verification: VerificationResult
    lowered: LoweredCircuit | None = None
    lowered_verification: LoweredVerificationResult | None = None
    resources: ResourceRecord | None = None
    failure_reason: str | None = None

    @property
    def eligible(self) -> bool:
        return (
            self.candidate.accounting_status == "emitted"
            and self.candidate.status == "success"
            and self.ideal_verification.status == "verified_ideal_semantics"
            and self.lowered_verification is not None
            and self.lowered_verification.status.startswith("verified_lowered_")
            and self.resources is not None
            and self.failure_reason is None
        )

    @property
    def resource_tuple(self) -> tuple[int, int, int] | None:
        if self.resources is None:
            return None
        return (
            self.resources.t_count,
            self.resources.t_depth,
            self.resources.peak_workspace,
        )

    def summary(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "method": self.candidate.method,
            "variant": self.candidate.variant,
            "status": self.candidate.status,
            "accounting_status": self.candidate.accounting_status,
            "ideal_verification": self.ideal_verification.status,
            "lowered_verification": (
                None
                if self.lowered_verification is None
                else self.lowered_verification.status
            ),
            "eligible": self.eligible,
            "resource_tuple": self.resource_tuple,
            "failure_reason": self.failure_reason or self.candidate.failure_reason,
        }

    def artifact(self) -> dict[str, Any]:
        value = self.summary()
        value["candidate"] = self.candidate.to_dict()
        value["ideal_verification_evidence"] = self.ideal_verification.to_dict()
        value["lowered_verification_evidence"] = (
            None
            if self.lowered_verification is None
            else self.lowered_verification.to_dict()
        )
        value["lowering"] = None if self.lowered is None else self.lowered.to_dict()
        value["resources"] = (
            None if self.resources is None else self.resources.to_dict()
        )
        return value


@dataclass
class SelectionResult:
    candidate: Candidate
    lowered: LoweredCircuit
    resources: ResourceRecord
    ideal_verification: VerificationResult
    lowered_verification: LoweredVerificationResult
    alternatives: list[EvaluatedAlternative]
    nondominated_labels: list[str]


def _dominates(first: tuple[int, int, int], second: tuple[int, int, int]) -> bool:
    return all(a <= b for a, b in zip(first, second, strict=True)) and any(
        a < b for a, b in zip(first, second, strict=True)
    )


def _nondominated(alternatives: list[EvaluatedAlternative]) -> list[str]:
    eligible = [item for item in alternatives if item.eligible]
    result = []
    for item in eligible:
        assert item.resource_tuple is not None
        if not any(
            other is not item
            and other.resource_tuple is not None
            and _dominates(other.resource_tuple, item.resource_tuple)
            for other in eligible
        ):
            result.append(item.label)
    return sorted(result)


def _rank(item: EvaluatedAlternative, objective: str) -> tuple:
    assert item.resources is not None
    resources = item.resources
    if objective == "t_depth":
        return (
            resources.t_depth,
            resources.t_count,
            resources.peak_workspace,
            item.label,
        )
    return (
        resources.t_count,
        resources.t_depth,
        resources.peak_workspace,
        item.label,
    )


def evaluate_alternatives(
    candidates: list[Candidate],
    total_error: float,
    synthesizer: RotationSynthesizer,
) -> list[EvaluatedAlternative]:
    results: list[EvaluatedAlternative] = []
    for index, candidate in enumerate(candidates):
        label = f"{candidate.method}:{candidate.variant}:{index}"
        ideal = verify_candidate(candidate)
        evaluated = EvaluatedAlternative(label, candidate, ideal)
        if candidate.status != "success":
            evaluated.failure_reason = candidate.failure_reason or "compilation failed"
        elif candidate.accounting_status != "emitted":
            evaluated.failure_reason = "non-emitted alternatives are ineligible"
        elif ideal.status != "verified_ideal_semantics":
            evaluated.failure_reason = f"ideal verification returned {ideal.status}"
        else:
            try:
                evaluated.lowered = lower_candidate(candidate, total_error, synthesizer)
                evaluated.lowered_verification = verify_lowered_circuit(
                    evaluated.lowered, total_error
                )
                if not evaluated.lowered_verification.status.startswith(
                    "verified_lowered_"
                ):
                    evaluated.failure_reason = evaluated.lowered_verification.message
                else:
                    evaluated.resources = estimate_resources(evaluated.lowered)
            except Exception as exc:
                evaluated.failure_reason = str(exc)
        results.append(evaluated)
    return results


def select_lowered_candidate(
    candidates: list[Candidate],
    total_error: float,
    synthesizer: RotationSynthesizer,
    *,
    selected_method: str,
    objective: str,
    preferred_method: str | None = None,
) -> SelectionResult:
    alternatives = evaluate_alternatives(candidates, total_error, synthesizer)
    eligible = [item for item in alternatives if item.eligible]
    if not eligible:
        reasons = "; ".join(
            f"{item.label}: {item.failure_reason}" for item in alternatives
        )
        raise RuntimeError(f"no eligible emitted alternative: {reasons}")
    if objective == "pareto" and preferred_method is not None:
        preferred = [
            item for item in eligible if item.candidate.method == preferred_method
        ]
        chosen = None
        for item in sorted(preferred, key=lambda value: _rank(value, "t_count")):
            assert item.resource_tuple is not None
            if all(
                other is item
                or other.resource_tuple is None
                or _dominates(item.resource_tuple, other.resource_tuple)
                or item.resource_tuple == other.resource_tuple
                for other in eligible
            ):
                chosen = item
                break
        if chosen is None:
            nonpreferred = [
                item for item in eligible if item.candidate.method != preferred_method
            ]
            chosen = min(nonpreferred or eligible, key=lambda value: _rank(value, "t_count"))
    else:
        chosen = min(eligible, key=lambda value: _rank(value, objective))

    nondominated = _nondominated(alternatives)
    selection_trace = {
        "action": "full_circuit_objective_selection",
        "objective": objective,
        "selected": chosen.label,
        "nondominated": nondominated,
        "alternatives": [item.summary() for item in alternatives],
    }
    candidate = replace(
        chosen.candidate,
        method=selected_method,
        selected_from=chosen.label,
        objective=objective,
        parameters={
            **chosen.candidate.parameters,
            "selection_objective": objective,
            "selection_alternatives": [item.summary() for item in alternatives],
            "nondominated_alternatives": nondominated,
        },
        transformation_trace=list(chosen.candidate.transformation_trace)
        + [selection_trace],
    )
    assert chosen.lowered is not None
    assert chosen.resources is not None
    assert chosen.lowered_verification is not None
    lowered = replace(chosen.lowered, candidate=candidate)
    resources = replace(
        chosen.resources,
        accounting_status=candidate.accounting_status,
    )
    return SelectionResult(
        candidate=candidate,
        lowered=lowered,
        resources=resources,
        ideal_verification=chosen.ideal_verification,
        lowered_verification=chosen.lowered_verification,
        alternatives=alternatives,
        nondominated_labels=nondominated,
    )
