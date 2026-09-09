from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

from .circuit import Candidate
from .lowering import LoweredCircuit, RotationSynthesizer, lower_candidate
from .resources import ResourceRecord, characterize_tradeoff, estimate_resources
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
    constraint_failure: str | None = None
    objective_value: float | None = None

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

    @property
    def feasible(self) -> bool:
        return self.eligible and self.constraint_failure is None

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
            "feasible": self.feasible,
            "resource_tuple": self.resource_tuple,
            "failure_reason": self.failure_reason or self.candidate.failure_reason,
            "constraint_failure": self.constraint_failure,
            "objective_value": self.objective_value,
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
        value["tradeoff"] = (
            None
            if self.lowered is None
            else characterize_tradeoff(self.lowered).to_dict()
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
    limits: "SelectionLimits"
    objective: "FinalObjective"


@dataclass(frozen=True)
class SelectionLimits:
    t_count: int | None = None
    t_depth: int | None = None
    ancilla: int | None = None

    def __post_init__(self) -> None:
        for name in ("t_count", "t_depth", "ancilla"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise ValueError(f"{name} limit must be a non-negative integer or null")

    @classmethod
    def from_value(
        cls, value: "SelectionLimits | dict[str, int | None] | None"
    ) -> "SelectionLimits":
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        unknown = set(value) - {"t_count", "t_depth", "ancilla"}
        if unknown:
            raise ValueError(f"unknown selection limits: {sorted(unknown)}")
        return cls(**value)

    def to_dict(self) -> dict[str, int | None]:
        return {
            "t_count": self.t_count,
            "t_depth": self.t_depth,
            "ancilla": self.ancilla,
        }

    def violation(self, resources: ResourceRecord) -> str | None:
        checks = (
            ("t_count", resources.t_count, self.t_count),
            ("t_depth", resources.t_depth, self.t_depth),
            ("ancilla", resources.peak_workspace, self.ancilla),
        )
        failures = [
            f"{name}={actual} exceeds {limit}"
            for name, actual, limit in checks
            if limit is not None and actual > limit
        ]
        return ", ".join(failures) or None


@dataclass(frozen=True)
class FinalObjective:
    mode: str = "single"
    metric: str = "t_count"
    t_weight: float = 0.0
    depth_weight: float = 0.0
    ancilla_weight: float = 0.0
    t_reference: float = 1.0
    depth_reference: float = 1.0
    ancilla_reference: float = 1.0

    def __post_init__(self) -> None:
        if self.mode not in {"single", "balance"}:
            raise ValueError("objective mode must be 'single' or 'balance'")
        if self.metric not in {"t_count", "t_depth", "ancilla"}:
            raise ValueError(f"unsupported objective metric {self.metric!r}")
        numeric = (
            self.t_weight,
            self.depth_weight,
            self.ancilla_weight,
            self.t_reference,
            self.depth_reference,
            self.ancilla_reference,
        )
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in numeric):
            raise ValueError("objective weights and references must be finite numbers")
        if any(value < 0 for value in self.weights):
            raise ValueError("objective weights must be non-negative")
        if self.mode == "balance" and not any(self.weights):
            raise ValueError("balance objective weights cannot all be zero")
        if any(value <= 0 for value in self.references):
            raise ValueError("objective references must be positive")

    @property
    def weights(self) -> tuple[float, float, float]:
        return (self.t_weight, self.depth_weight, self.ancilla_weight)

    @property
    def references(self) -> tuple[float, float, float]:
        return (self.t_reference, self.depth_reference, self.ancilla_reference)

    @property
    def name(self) -> str:
        return self.metric if self.mode == "single" else "balance"

    @classmethod
    def from_value(cls, value: "FinalObjective | str | dict[str, Any]") -> "FinalObjective":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(metric=value)
        unknown = set(value) - {"mode", "metric", "weights", "references"}
        if unknown:
            raise ValueError(f"unknown objective fields: {sorted(unknown)}")
        mode = str(value.get("mode", "single"))
        metric = str(value.get("metric", "t_count"))
        weights = value.get("weights", {})
        references = value.get("references", {})
        if not isinstance(weights, dict) or not isinstance(references, dict):
            raise ValueError("objective weights and references must be mappings")
        return cls(
            mode=mode,
            metric=metric,
            t_weight=float(weights.get("t_count", 0.0)),
            depth_weight=float(weights.get("t_depth", 0.0)),
            ancilla_weight=float(weights.get("ancilla", 0.0)),
            t_reference=float(references.get("t_count", 1.0)),
            depth_reference=float(references.get("t_depth", 1.0)),
            ancilla_reference=float(references.get("ancilla", 1.0)),
        )

    def validate_limits(self, limits: SelectionLimits) -> None:
        if self.mode == "single" and self.metric == "ancilla":
            if limits.t_count is None or limits.t_depth is None:
                raise ValueError(
                    "ancilla objective requires explicit t_count and t_depth limits"
                )

    def value(self, resources: ResourceRecord) -> float:
        if self.mode == "single":
            return float(
                {
                    "t_count": resources.t_count,
                    "t_depth": resources.t_depth,
                    "ancilla": resources.peak_workspace,
                }[self.metric]
            )
        values = (
            resources.t_count,
            resources.t_depth,
            resources.peak_workspace,
        )
        return sum(
            weight * value / reference
            for weight, value, reference in zip(
                self.weights, values, self.references, strict=True
            )
        )

    def rank(self, resources: ResourceRecord, label: str) -> tuple:
        if self.mode == "balance":
            return (
                self.value(resources),
                resources.t_count,
                resources.t_depth,
                resources.peak_workspace,
                label,
            )
        values = {
            "t_count": (
                resources.t_count,
                resources.t_depth,
                resources.peak_workspace,
            ),
            "t_depth": (
                resources.t_depth,
                resources.t_count,
                resources.peak_workspace,
            ),
            "ancilla": (
                resources.peak_workspace,
                resources.t_count,
                resources.t_depth,
            ),
        }
        return (*values[self.metric], label)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"mode": self.mode}
        if self.mode == "single":
            value["metric"] = self.metric
        else:
            value["weights"] = dict(
                zip(("t_count", "t_depth", "ancilla"), self.weights, strict=True)
            )
            value["references"] = dict(
                zip(("t_count", "t_depth", "ancilla"), self.references, strict=True)
            )
        return value


class NoFeasibleAlternativeError(RuntimeError):
    """Raised when valid alternatives exist but every one violates a hard limit."""


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


def _rank(item: EvaluatedAlternative, objective: FinalObjective) -> tuple:
    assert item.resources is not None
    return objective.rank(item.resources, item.label)


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
    objective: FinalObjective | str | dict[str, Any],
    limits: SelectionLimits | dict[str, int | None] | None = None,
) -> SelectionResult:
    normalized_limits = SelectionLimits.from_value(limits)
    normalized_objective = FinalObjective.from_value(objective)
    normalized_objective.validate_limits(normalized_limits)
    alternatives = evaluate_alternatives(candidates, total_error, synthesizer)
    chosen = select_evaluated_alternative(
        alternatives, normalized_objective, normalized_limits
    )
    nondominated = _nondominated(alternatives)
    selection_trace = {
        "action": "full_circuit_objective_selection",
        "objective": normalized_objective.to_dict(),
        "limits": normalized_limits.to_dict(),
        "selected": chosen.label,
        "nondominated": nondominated,
        "alternatives": [item.summary() for item in alternatives],
    }
    candidate = replace(
        chosen.candidate,
        method=selected_method,
        selected_from=chosen.label,
        objective=normalized_objective.name,
        parameters={
            **chosen.candidate.parameters,
            "selection_objective": normalized_objective.to_dict(),
            "selection_limits": normalized_limits.to_dict(),
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
        limits=normalized_limits,
        objective=normalized_objective,
    )


def select_evaluated_alternative(
    alternatives: list[EvaluatedAlternative],
    objective: FinalObjective | str | dict[str, Any],
    limits: SelectionLimits | dict[str, int | None] | None = None,
) -> EvaluatedAlternative:
    """Select from measured complete circuits without lowering them again."""
    normalized_limits = SelectionLimits.from_value(limits)
    normalized_objective = FinalObjective.from_value(objective)
    normalized_objective.validate_limits(normalized_limits)
    eligible = [item for item in alternatives if item.eligible]
    if not eligible:
        reasons = "; ".join(
            f"{item.label}: {item.failure_reason}" for item in alternatives
        )
        raise RuntimeError(f"no eligible emitted alternative: {reasons}")
    for item in eligible:
        assert item.resources is not None
        item.constraint_failure = normalized_limits.violation(item.resources)
        item.objective_value = normalized_objective.value(item.resources)
    feasible = [item for item in eligible if item.feasible]
    if not feasible:
        reasons = "; ".join(
            f"{item.label}: {item.constraint_failure}" for item in eligible
        )
        raise NoFeasibleAlternativeError(f"no feasible alternative: {reasons}")
    return min(feasible, key=lambda value: _rank(value, normalized_objective))
