from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import cmp_to_key
import json
from pathlib import Path
from typing import Any

from .selection import (
    FinalObjective,
    compare_objective_outcomes,
    compare_objective_values,
    dominates_resources,
)


def _identity(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("code_revision")),
        str(row.get("config_hash")),
        str(row.get("manifest_hash")),
        str(row.get("backend_environment_hash")),
        json.dumps(row.get("objective"), sort_keys=True),
    )


def _case_key(row: dict[str, Any]) -> tuple:
    return (
        row.get("target_hash"),
        row.get("angle_id"),
        row.get("error_budget"),
        row.get("workspace_budget"),
        row.get("model_profile"),
    )


def _row_order(row: dict[str, Any]) -> tuple:
    return (
        row.get("case_id", ""),
        row.get("workspace_budget", -1),
        row.get("policy", ""),
    )


def _resources(row: dict[str, Any]) -> str:
    if row.get("status") != "success":
        return "n/a"
    return f"({row['t_count']}, {row['t_depth']}, {row['peak_workspace']})"


def _cell(value: Any) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def _backend_summary(rows: list[dict[str, Any]]) -> list[str]:
    observed: dict[str, dict[str, Any]] = {}
    for row in rows:
        for name, value in row.get("backend_status", {}).items():
            observed[name] = value
    lines = [
        "| Backend | Revision | Status | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for name, value in sorted(observed.items()):
        detail = value.get("reason") or ", ".join(value.get("actions", [])) or "exact API"
        lines.append(
            f"| {name} | {value.get('revision', 'n/a')} | "
            f"{value.get('status', 'unknown')} | {detail} |"
        )
    if not observed:
        lines.append("| none | n/a | unavailable | no backend status recorded |")
    return lines


@dataclass
class _ComparisonCounts:
    wins: int = 0
    ties: int = 0
    regressions: int = 0
    denominator: int = 0
    tie_break_wins: int = 0
    tie_break_ties: int = 0
    tie_break_regressions: int = 0
    pareto_dominates: int = 0
    pareto_equal: int = 0
    pareto_dominated: int = 0
    pareto_incomparable: int = 0


def _resource_tuple(row: dict[str, Any]) -> tuple[int, int, int]:
    return (int(row["t_count"]), int(row["t_depth"]), int(row["peak_workspace"]))


def _comparison_counts(
    groups: dict[tuple, list[dict[str, Any]]], comparator_policies: set[str]
) -> _ComparisonCounts:
    counts = _ComparisonCounts()
    for rows in groups.values():
        adaptive = next(
            (row for row in rows if row["policy"] == "adaptive" and row["status"] == "success"),
            None,
        )
        comparators = [
            row
            for row in rows
            if row["policy"] in comparator_policies and row["status"] == "success"
        ]
        if adaptive is None or not comparators:
            continue
        objective = FinalObjective.from_value(adaptive["objective"])

        def compare_rows(first: dict[str, Any], second: dict[str, Any]) -> int:
            result = compare_objective_outcomes(
                objective,
                float(first["objective_value"]),
                _resource_tuple(first),
                float(second["objective_value"]),
                _resource_tuple(second),
            )
            if result:
                return result
            return (first["policy"] > second["policy"]) - (
                first["policy"] < second["policy"]
            )

        reference = min(comparators, key=cmp_to_key(compare_rows))
        counts.denominator += 1
        scalar = compare_objective_values(
            float(adaptive["objective_value"]),
            float(reference["objective_value"]),
        )
        if scalar < 0:
            counts.wins += 1
        elif scalar > 0:
            counts.regressions += 1
        else:
            counts.ties += 1
            physical = compare_objective_outcomes(
                objective,
                float(adaptive["objective_value"]),
                _resource_tuple(adaptive),
                float(reference["objective_value"]),
                _resource_tuple(reference),
            )
            if physical < 0:
                counts.tie_break_wins += 1
            elif physical > 0:
                counts.tie_break_regressions += 1
            else:
                counts.tie_break_ties += 1
        adaptive_resources = _resource_tuple(adaptive)
        reference_resources = _resource_tuple(reference)
        if dominates_resources(adaptive_resources, reference_resources):
            counts.pareto_dominates += 1
        elif adaptive_resources == reference_resources:
            counts.pareto_equal += 1
        elif dominates_resources(reference_resources, adaptive_resources):
            counts.pareto_dominated += 1
        else:
            counts.pareto_incomparable += 1
    return counts


def _comparison_text(label: str, counts: _ComparisonCounts) -> str:
    return (
        f"{label}: {counts.wins} wins, {counts.ties} ties, "
        f"{counts.regressions} regressions on {counts.denominator} matched cases. "
        f"Within scalar ties, physical tie-breaks are {counts.tie_break_wins} wins, "
        f"{counts.tie_break_ties} ties, {counts.tie_break_regressions} regressions. "
        f"Pareto relation is {counts.pareto_dominates} dominates, "
        f"{counts.pareto_equal} equal, {counts.pareto_dominated} dominated, "
        f"{counts.pareto_incomparable} incomparable."
    )


def _adaptive_comparison(groups: dict[tuple, list[dict[str, Any]]]) -> str:
    static = _comparison_counts(groups, {"static_t", "static_depth", "static_ancilla", "static_balanced"})
    fixed = _comparison_counts(groups, {"fixed_count_depth", "fixed_depth_count"})
    frozen = _comparison_counts(groups, {"frozen"})
    return (
        _comparison_text(
            "Adaptive versus the combined static-preference portfolio", static
        )
        + " "
        + _comparison_text(
            "Versus the fixed successive-sequence portfolio", fixed
        )
        + " "
        + _comparison_text("Versus frozen priorities", frozen)
        + " Static and fixed "
        "portfolios split the same total call budget; each policy sees the same roots and actions."
    )


def _mechanism_conclusion(
    groups: dict[tuple, list[dict[str, Any]]], rows: list[dict[str, Any]]
) -> str:
    ancilla_gain = any(
        step.get("status") == "accepted" and step.get("a_after", 0) > step.get("a_before", 0)
        and step.get("d_after", 0) < step.get("d_before", 0)
        for row in rows for step in row.get("trace", [])
        if step.get("action_backend") == "phase_ancilla:parallel_phase"
    )
    chained = any(
        step.get("status") == "accepted" and "|" in step.get("parent_id", "")
        for row in rows for step in row.get("trace", [])
    )
    static = _comparison_counts(groups, {"static_t", "static_depth", "static_ancilla", "static_balanced"})
    fixed = _comparison_counts(groups, {"fixed_count_depth", "fixed_depth_count"})
    frozen = _comparison_counts(groups, {"frozen"})
    return (
        f"Ancilla-for-depth action observed: {'yes' if ancilla_gain else 'no'}. "
        f"Verified successive transformations observed: {'yes' if chained else 'no'}. "
        f"Adaptive beats the matched static portfolio in {static.wins}/{static.denominator} "
        f"and the matched fixed-sequence portfolio in {fixed.wins}/{fixed.denominator} cases. "
        f"Versus frozen priorities: {frozen.wins} wins, {frozen.ties} ties, "
        f"{frozen.regressions} regressions. "
        "Certified scratch reuse is implemented; an application-level benefit "
        "has not been established."
    )


def render_comparison_report(rows: list[dict[str, Any]], results_path: Path) -> str:
    identities = {_identity(row) for row in rows}
    if len(identities) > 1:
        raise ValueError("result report mixes revisions, configurations, or objectives")
    statuses = Counter(row.get("status", "unknown") for row in rows)
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_case_key(row)].append(row)
    for case_rows in groups.values():
        if len({json.dumps(row.get("limits"), sort_keys=True) for row in case_rows}) > 1:
            raise ValueError("result report mixes hard limits within a matched case")
    objective = rows[0].get("objective", {}) if rows else {}
    limits_by_workspace = {
        str(row["workspace_budget"]): row.get("limits", {}) for row in rows
    }
    distinct_limits = {json.dumps(value, sort_keys=True) for value in limits_by_workspace.values()}
    limits_description = (
        f"Hard limits: `{next(iter(distinct_limits))}`."
        if len(distinct_limits) == 1 else
        f"Hard limits by workspace budget: `{json.dumps(limits_by_workspace, sort_keys=True)}`."
    )
    lines = [
        "# Adaptive Resource Tradeoff Study",
        "",
        f"Results: `{results_path}`",
        "",
        f"Code revision: `{rows[0].get('code_revision', 'unknown') if rows else 'unknown'}`. "
        f"Config hash: `{rows[0].get('config_hash', 'unknown') if rows else 'unknown'}`. "
        f"Manifest hash: `{rows[0].get('manifest_hash', 'unknown') if rows else 'unknown'}`.",
        "",
        f"Fixed final objective: `{json.dumps(objective, sort_keys=True)}`. "
        + limits_description,
        "",
        "## Integrated Methods",
        "",
        *_backend_summary(rows),
        "",
        "Unsupported, timed-out, and verification-inconclusive outputs are not "
        "treated as feasible alternatives.",
        "",
        "## Policy Outcomes",
        "",
        "`Resources` is `(T, scheduled T-depth, allocated logical ancillas)`. The "
        "objective and tie-breaks remain fixed across every row.",
        "",
        "| Case | Angle | Workspace budget | Policy | Status | Resources | J | Calls | Total seconds |",
        "| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in sorted(rows, key=_row_order):
        objective_value = row.get("objective_value")
        lines.append(
            f"| {_cell(row.get('case_id', 'unknown'))} | {_cell(row.get('angle_id', 'unknown'))} | {row.get('workspace_budget', 'n/a')} | "
            f"{_cell(row.get('policy', 'unknown'))} | "
            f"{row.get('status', 'unknown')} | {_resources(row)} | "
            f"{objective_value if objective_value is not None else 'n/a'} | "
            f"{row.get('backend_calls', 0)} | {float(row.get('total_seconds', 0)):.3f} |"
        )
    lines.extend(["", _adaptive_comparison(groups), ""])

    lines.extend([
        "## Portfolio Cost",
        "",
        "Shared root preparation is counted once per portfolio; search wall time "
        "includes backend, verification, scheduling, and controller work.",
        "",
        "| Case | Angle | Workspace budget | Portfolio | Calls | Wall seconds | Best J |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: |",
    ])
    for case_rows in groups.values():
        sample = case_rows[0]
        for label, names in (
            ("adaptive", {"adaptive"}),
            ("frozen", {"frozen"}),
            ("static combined", {"static_t", "static_depth", "static_ancilla", "static_balanced"}),
            ("fixed combined", {"fixed_count_depth", "fixed_depth_count"}),
        ):
            members = [row for row in case_rows if row.get("policy") in names]
            if not members:
                continue
            roots = max(float(row.get("root_seconds", 0)) for row in members)
            seconds = roots + sum(float(row.get("search_seconds", 0)) for row in members)
            values = [float(row["objective_value"]) for row in members if row.get("status") == "success"]
            lines.append(
                f"| {_cell(sample['case_id'])} | {_cell(sample['angle_id'])} | "
                f"{sample['workspace_budget']} | {label} | "
                f"{sum(row.get('backend_calls', 0) for row in members)} | {seconds:.3f} | "
                f"{min(values) if values else 'n/a'} |"
            )

    lines.extend(
        [
            "## Paired Optimization",
            "",
            "Accepted steps on each selected circuit's parent chain.",
            "",
            "| Case | Workspace budget | Policy | Backend action | Before | After |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    accepted = 0
    for row in sorted(rows, key=_row_order):
        by_output = {
            step.get("output_id"): step for step in row.get("trace", [])
            if step.get("status") in {"accepted", "unchanged"}
        }
        selected = row.get("selected") or {}
        chain = []
        current = selected.get("label")
        while current in by_output:
            step = by_output[current]
            chain.append(step)
            current = step.get("parent_id")
        for step in reversed(chain):
            accepted += 1
            before = f"({step['t_before']}, {step['d_before']}, {step['a_before']})"
            after = f"({step['t_after']}, {step['d_after']}, {step['a_after']})"
            lines.append(
                f"| {_cell(row['case_id'])} ({_cell(row.get('angle_id', ''))}) | {row.get('workspace_budget', 'n/a')} | "
                f"{_cell(row['policy'])} | {_cell(step['action_backend'])} | "
                f"{before} | {after} |"
            )
    if not accepted:
        lines.append("| n/a | n/a | n/a | no accepted backend action | n/a | n/a |")

    trace_rows = [
        row
        for row in rows
        if row.get("policy") == "adaptive" and row.get("trace")
    ]
    trace_row = max(
        trace_rows,
        key=lambda row: (
            any(step.get("a_after", 0) > step.get("a_before", 0) for step in row["trace"]),
            any("|" in step.get("parent_id", "") for step in row["trace"]),
            -float(row.get("objective_value") or float("inf")),
        ), default=None,
    )
    trace_case = (
        "No adaptive case has an attempt trace."
        if trace_row is None else
        f"Case: `{trace_row['case_id']}`, workspace budget: `{trace_row['workspace_budget']}`."
    )
    lines.extend(
        [
            "",
            "## Decision Trace",
            "",
            "Attempt log for one adaptive case, recorded when each decision occurred. "
            "`P` lists current count/depth/ancilla pressure plus objective weights.",
            "",
            trace_case,
            "",
            "| Step | Parent | Region | Action | Scratch | Scratch wires | P | Priority and reason | T | D | A | J | Seconds | Status |",
            "| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    if trace_row is None:
        lines.append("| 0 | n/a | n/a | none | 0 | n/a | n/a | no adaptive attempt | n/a | n/a | n/a | n/a | 0 | none |")
    else:
        for step in trace_row["trace"]:
            scratch_wires = (
                f"alloc={step.get('allocated_scratch_wire_ids', [])}, "
                f"reuse={step.get('reused_scratch_wire_ids', [])}, "
                f"release={step.get('released_scratch_wire_ids', [])}"
            )
            lines.append(
                f"| {step['step']} | {_cell(step.get('parent_id', ''))} | {_cell(step['region'])} | "
                f"{_cell(step['action_backend'])} | {step.get('allowance', 0)} | "
                f"{_cell(scratch_wires)} | "
                f"{_cell(str(tuple(round(value, 3) for value in step.get('priority_vector', []))))} | "
                f"{step['local_priority']:.4f}: {_cell(step['reason'].splitlines()[0])} | "
                f"{step['t_before']} -> {step['t_after']} | "
                f"{step['d_before']} -> {step['d_after']} | "
                f"{step['a_before']} -> {step['a_after']} | "
                f"{step['j_before']:.6g} -> {step['j_after']:.6g} | "
                f"{step['backend_seconds']:.3f} | {step.get('status', 'unknown')} |"
            )

    pareto: dict[tuple[str, str, int, int, int, int], set[str]] = defaultdict(set)
    for row in rows:
        for point in row.get("pareto", []):
            resources = tuple(point["resources"])
            key = (row["case_id"], row.get("angle_id", ""), row["workspace_budget"], *resources)
            pareto[key].add(point["label"])
    lines.extend(
        [
            "",
            "## Final Pareto Points",
            "",
            "Each policy row's checksummed circuit artifact contains emitted gates and "
            "a replayable proof chain for every listed alternative.",
            "",
            "| Case | Angle | Workspace budget | T | D | A | Implementations |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for key, labels in sorted(pareto.items()):
        case_id, angle_id, workspace, t_count, t_depth, ancilla = key
        if any(
            other[:3] == key[:3]
            and all(left <= right for left, right in zip(other[3:], key[3:], strict=True))
            and any(left < right for left, right in zip(other[3:], key[3:], strict=True))
            for other in pareto
        ):
            continue
        lines.append(
            f"| {_cell(case_id)} | {_cell(angle_id)} | {workspace} | {t_count} | {t_depth} | {ancilla} | "
            f"{_cell(', '.join(sorted(labels)[:3]))} |"
        )
    if not pareto:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | no verified point |")

    lines.extend(
        [
            "",
            "## Mechanism Conclusion",
            "",
            _mechanism_conclusion(groups, rows),
            "",
            "Post-optimization T is reported only as a total because optimized gates "
            "no longer have a reliable arithmetic-versus-rotation attribution.",
            "",
        ]
    )
    if statuses:
        lines.append(
            "Recorded statuses: "
            + ", ".join(f"`{name}`={count}" for name, count in sorted(statuses.items()))
            + "."
        )
        lines.append("")
    return "\n".join(lines)
