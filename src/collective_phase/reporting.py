from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


def _identity(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("code_revision")),
        str(row.get("config_hash")),
        str(row.get("manifest_hash")),
        json.dumps(row.get("objective"), sort_keys=True),
        json.dumps(row.get("limits"), sort_keys=True),
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
    return str(value).replace("|", "\\|")


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


def _comparison_counts(
    groups: dict[tuple, list[dict[str, Any]]], comparator_policies: set[str]
) -> tuple[int, int, int, int]:
    wins = ties = regressions = denominator = 0
    for rows in groups.values():
        adaptive = next(
            (row for row in rows if row["policy"] == "adaptive_lookahead" and row["status"] == "success"),
            None,
        )
        comparators = [
            row
            for row in rows
            if row["policy"] in comparator_policies and row["status"] == "success"
        ]
        if adaptive is None or not comparators:
            continue
        denominator += 1
        reference = min(float(row["objective_value"]) for row in comparators)
        actual = float(adaptive["objective_value"])
        if actual < reference - 1e-12:
            wins += 1
        elif actual > reference + 1e-12:
            regressions += 1
        else:
            ties += 1
    return wins, ties, regressions, denominator


def _adaptive_comparison(groups: dict[tuple, list[dict[str, Any]]]) -> str:
    fixed_priority = {
        row["policy"]
        for rows in groups.values()
        for row in rows
        if row.get("policy", "").startswith("static_")
    }
    static = _comparison_counts(groups, fixed_priority)
    nonadaptive = _comparison_counts(groups, fixed_priority | {"fixed_order"})
    if not static[3]:
        return "No matched adaptive/static comparison is available."
    return (
        f"Against the best fixed-priority endpoint, adaptive lookahead has {static[0]} "
        f"wins, {static[1]} ties, and {static[2]} regressions on {static[3]} matched "
        f"feasible cases. Against the best nonadaptive endpoint including fixed order, "
        f"it has {nonadaptive[0]} wins, {nonadaptive[1]} ties, and {nonadaptive[2]} "
        f"regressions on {nonadaptive[3]} cases. Backend calls are shown per row; the "
        "static weight multi-start budget is split across its predeclared vectors."
    )


def _trace_improvement(row: dict[str, Any]) -> float:
    trace = row.get("trace", [])
    if not trace:
        return float("-inf")
    return float(trace[0]["j_before"]) - float(trace[-1]["j_after"])


def _mechanism_conclusion(
    groups: dict[tuple, list[dict[str, Any]]], rows: list[dict[str, Any]]
) -> str:
    enabling = any(
        row.get("policy") == "adaptive_lookahead"
        and len(row.get("trace", [])) >= 2
        and row["trace"][0].get("provisional")
        and row["trace"][0]["j_after"] > row["trace"][0]["j_before"]
        and row["trace"][-1]["j_after"] < row["trace"][0]["j_before"]
        for row in rows
    )
    fixed_priority = {
        row["policy"]
        for row in rows
        if row.get("policy", "").startswith("static_")
    }
    nonadaptive = _comparison_counts(groups, fixed_priority | {"fixed_order"})
    if not nonadaptive[3]:
        return (
            "No matched adaptive/static mechanism conclusion is available for "
            "this run."
        )
    mechanism = (
        "At least one accepted sequence crosses a temporarily worse construction "
        "state before exact joint optimization improves the fixed final objective. "
        if enabling
        else "No accepted sequence demonstrates a temporarily worse enabling state. "
    )
    if nonadaptive[0] == 0:
        return (
            mechanism
            + "The best nonadaptive policy matches or beats every adaptive endpoint, "
            "so these rows do not establish an adaptive-priority advantage."
        )
    return (
        mechanism
        + f"Adaptive lookahead beats the best nonadaptive endpoint on {nonadaptive[0]} "
        f"of {nonadaptive[3]} matched cases; independent evaluation is still required."
    )


def render_comparison_report(rows: list[dict[str, Any]], results_path: Path) -> str:
    identities = {_identity(row) for row in rows}
    if len(identities) > 1:
        raise ValueError("result report mixes revisions, configurations, or objectives")
    statuses = Counter(row.get("status", "unknown") for row in rows)
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_case_key(row)].append(row)
    objective = rows[0].get("objective", {}) if rows else {}
    limits = rows[0].get("limits", {}) if rows else {}
    lines = [
        "# Adaptive Resource Tradeoff Study",
        "",
        f"Results: `{results_path}`",
        "",
        f"Fixed final objective: `{json.dumps(objective, sort_keys=True)}`. "
        f"Hard limits: `{json.dumps(limits, sort_keys=True)}`.",
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
        "`Resources` is `(T, scheduled T-depth, peak allocated workspace)`. The "
        "objective and tie-breaks remain fixed across every row.",
        "",
        "| Case | Workspace budget | Policy | Status | Resources | J | Evaluations | Backend calls | Backend seconds |",
        "| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(rows, key=_row_order):
        objective_value = row.get("objective_value")
        lines.append(
            f"| {_cell(row.get('case_id', 'unknown'))} | {row.get('workspace_budget', 'n/a')} | "
            f"{_cell(row.get('policy', 'unknown'))} | "
            f"{row.get('status', 'unknown')} | {_resources(row)} | "
            f"{objective_value if objective_value is not None else 'n/a'} | "
            f"{row.get('evaluations', 0)} | {row.get('backend_calls', 0)} | "
            f"{float(row.get('backend_seconds', 0)):.6f} |"
        )
    lines.extend(["", _adaptive_comparison(groups), ""])

    lines.extend(
        [
            "## Paired Optimization",
            "",
            "These are accepted backend steps only; construction-seed transitions "
            "are listed separately in the decision trace.",
            "",
            "| Case | Workspace budget | Policy | Backend action | Before | After |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    accepted = 0
    for row in sorted(rows, key=_row_order):
        for step in row.get("trace", []):
            if step.get("provisional"):
                continue
            accepted += 1
            before = f"({step['t_before']}, {step['d_before']}, {step['a_before']})"
            after = f"({step['t_after']}, {step['d_after']}, {step['a_after']})"
            lines.append(
                f"| {_cell(row['case_id'])} | {row.get('workspace_budget', 'n/a')} | "
                f"{_cell(row['policy'])} | {_cell(step['action_backend'])} | "
                f"{before} | {after} |"
            )
    if not accepted:
        lines.append("| n/a | n/a | n/a | no accepted backend action | n/a | n/a |")

    trace_rows = [
        row
        for row in rows
        if row.get("policy") == "adaptive_lookahead" and row.get("trace")
    ]
    trace_row = max(trace_rows, key=_trace_improvement, default=None)
    lines.extend(
        [
            "",
            "## Decision Trace",
            "",
            "| Step | Region | Action/backend | Reason | Priority | T | D | A | J | Evaluations | Seconds | State |",
            "| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    if trace_row is None:
        lines.append("| 0 | n/a | none | no accepted adaptive action | 0 | n/a | n/a | n/a | n/a | 0 | 0 | final |")
    else:
        for step in trace_row["trace"]:
            lines.append(
                f"| {step['step']} | {_cell(step['region'])} | "
                f"{_cell(step['action_backend'])} | {_cell(step['reason'])} | "
                f"{step['local_priority']:.4f} | "
                f"{step['t_before']} -> {step['t_after']} | "
                f"{step['d_before']} -> {step['d_after']} | "
                f"{step['a_before']} -> {step['a_after']} | "
                f"{step['j_before']:.6g} -> {step['j_after']:.6g} | "
                f"{step['evaluations']} | {step['backend_seconds']:.6f} | "
                f"{'provisional' if step['provisional'] else 'accepted'} |"
            )

    pareto: dict[tuple[str, int, int, int, int], set[str]] = defaultdict(set)
    for row in rows:
        for point in row.get("pareto", []):
            resources = tuple(point["resources"])
            key = (row["case_id"], row["workspace_budget"], *resources)
            pareto[key].add(point["label"])
    lines.extend(
        [
            "",
            "## Final Pareto Points",
            "",
            "| Case | Workspace budget | T | D | A | Implementations |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for key, labels in sorted(pareto.items()):
        case_id, workspace, t_count, t_depth, ancilla = key
        lines.append(
            f"| {_cell(case_id)} | {workspace} | {t_count} | {t_depth} | {ancilla} | "
            f"{_cell(', '.join(sorted(labels)))} |"
        )
    if not pareto:
        lines.append("| n/a | n/a | n/a | n/a | n/a | no verified point |")

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
