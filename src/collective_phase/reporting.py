from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _eligible(row: dict[str, Any]) -> bool:
    return bool(
        row.get("status") == "success"
        and row.get("primary_eligible")
        and str(row.get("lowered_verification_status", "")).startswith(
            "verified_lowered_"
        )
    )


def _dominates(first: dict[str, Any], second: dict[str, Any]) -> bool:
    first_cost = (
        int(first["t_count"]),
        int(first["t_depth"]),
        int(first["peak_workspace"]),
    )
    second_cost = (
        int(second["t_count"]),
        int(second["t_depth"]),
        int(second["peak_workspace"]),
    )
    return all(a <= b for a, b in zip(first_cost, second_cost, strict=True)) and any(
        a < b for a, b in zip(first_cost, second_cost, strict=True)
    )


def _rank(row: dict[str, Any], objective: str) -> tuple:
    stable_id = (row["method"], row.get("variant") or "")
    if objective == "t_depth":
        return (
            int(row["t_depth"]),
            int(row["t_count"]),
            int(row["peak_workspace"]),
            stable_id,
        )
    if objective == "ancilla":
        return (
            int(row["peak_workspace"]),
            int(row["t_count"]),
            int(row["t_depth"]),
            stable_id,
        )
    return (
        int(row["t_count"]),
        int(row["t_depth"]),
        int(row["peak_workspace"]),
        stable_id,
    )


def _comparison_key(row: dict[str, Any]) -> tuple:
    return tuple(
        row.get(key)
        for key in (
            "target_hash",
            "angle_id",
            "error_budget",
            "workspace_budget",
            "model_profile",
            "reuse_count",
        )
    )


def _label(row: dict[str, Any]) -> str:
    return f"{row['method']}:{row.get('variant') or 'unavailable'}"


def _policy_alternatives(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    for row in rows:
        internal = row.get("evaluated_alternatives") or []
        if internal and _eligible(row):
            for item in internal:
                resources = item.get("resource_tuple")
                if not item.get("eligible") or resources is None:
                    continue
                alternatives.append(
                    {
                        "method": item["method"],
                        "variant": item.get("variant"),
                        "t_count": resources[0],
                        "t_depth": resources[1],
                        "peak_workspace": resources[2],
                        "constraint_failure": item.get("constraint_failure"),
                    }
                )
        elif _eligible(row):
            alternatives.append(row)
    return alternatives


def render_comparison_report(
    rows: list[dict[str, Any]], results_path: Path
) -> str:
    """Render the default construction/check/compare study report."""
    study_identities = {
        (
            row.get("code_revision"),
            row.get("config_hash"),
            row.get("manifest_hash"),
            row.get("objective"),
            tuple(sorted((row.get("selection_limits") or {}).items())),
        )
        for row in rows
    }
    if len(study_identities) > 1:
        raise ValueError(
            "result report mixes revisions, configurations, or selection policies"
        )
    statuses = Counter(row.get("status", "unknown") for row in rows)
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_comparison_key(row)].append(row)
    objective = str(rows[0].get("objective", "t_count")) if rows else "t_count"
    limits = rows[0].get("selection_limits", {}) if rows else {}
    limit_text = ", ".join(
        f"{name}={value}"
        for name, value in limits.items()
        if value is not None
    ) or "none"

    lines = [
        "# Construction Tradeoff Study",
        "",
        f"Results: `{results_path}`",
        "",
        "This fixed study compares named circuit constructions under one common "
        "parity-phase target, lowering backend, and whole-circuit operator-norm "
        "error budget. Compilation time is diagnostic only.",
        "",
        f"Declared selection policy: `{objective}`; hard limits: {limit_text}.",
        "",
        "## Status",
        "",
    ]
    lines.extend(f"- `{status}`: {count}" for status, count in sorted(statuses.items()))

    lines.extend(
        [
            "",
            "## Construction Results",
            "",
            "Arithmetic T is the T cost outside synthesized rotations. Rotation T "
            "includes application rotations and any resource-state preparation.",
            "",
            "| Case | Method | Variant | Generic rotations | Arithmetic T | "
            "Rotation T | Total T | T-depth | Peak ancillas | Error | "
            "Verification scope | Evidence |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | --- | --- |",
        ]
    )
    for row in sorted(
        rows,
        key=lambda item: (
            item.get("stratum", ""),
            item.get("case_id", ""),
            item.get("method", ""),
        ),
    ):
        lines.append(
            f"| {row.get('case_id', 'unknown')} | {row.get('method', 'unknown')} | "
            f"{row.get('variant') or 'n/a'} | "
            f"{row.get('generic_application_rotations', 'n/a')} | "
            f"{row.get('arithmetic_t', 'n/a')} | {row.get('rotation_t', 'n/a')} | "
            f"{row.get('t_count', 'n/a')} | {row.get('t_depth', 'n/a')} | "
            f"{row.get('peak_workspace', 'n/a')} | {row.get('error_bound', 'n/a')} | "
            f"{row.get('verification_scope', 'not_run')} | "
            f"{row.get('evidence_level', 'unclassified')} / "
            f"{row.get('reproduction_quality', 'unreviewed')} |"
        )

    lines.extend(
        [
            "",
            "## Pareto And Selection",
            "",
            "The Pareto set uses `(T, T-depth, ancillas)` for every validated "
            "default-study construction. Selection then applies the declared hard "
            "limits and objective; limits are never relaxed.",
            "",
            "Each policy below selects among the same evaluated circuits. The "
            f"configuration declares `{objective}`; the other columns expose how "
            "preference alone changes the result.",
            "",
            "| Case | Pareto alternatives | T-count choice | T-depth choice | "
            "Ancilla choice |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    selected_rows: list[dict[str, Any]] = []
    for group_rows in sorted(groups.values(), key=lambda values: values[0]["case_id"]):
        eligible = _policy_alternatives(group_rows)
        pareto = [
            row
            for row in eligible
            if not any(other is not row and _dominates(other, row) for other in eligible)
        ]
        feasible = [row for row in eligible if row.get("constraint_failure") is None]
        choices = {
            policy: min(feasible, key=lambda row: _rank(row, policy))
            if feasible
            else None
            for policy in ("t_count", "t_depth", "ancilla")
        }
        chosen = choices.get(objective)
        top_level_feasible = [
            row
            for row in group_rows
            if _eligible(row) and row.get("constraint_failure") is None
        ]
        if top_level_feasible:
            selected_rows.append(
                min(top_level_feasible, key=lambda row: _rank(row, objective))
            )
        case_id = group_rows[0].get("case_id", "unknown")
        pareto_text = ", ".join(sorted(_label(row) for row in pareto)) or "none"
        choice_text = {
            policy: _label(value) if value is not None else "no feasible alternative"
            for policy, value in choices.items()
        }
        lines.append(
            f"| {case_id} | {pareto_text} | {choice_text['t_count']} | "
            f"{choice_text['t_depth']} | {choice_text['ancilla']} |"
        )

    arithmetic_total = sum(int(row.get("arithmetic_t") or 0) for row in selected_rows)
    rotation_total = sum(int(row.get("rotation_t") or 0) for row in selected_rows)
    dominant = (
        "rotation synthesis"
        if rotation_total > arithmetic_total
        else "reversible arithmetic"
        if arithmetic_total > rotation_total
        else "neither component"
    )
    independent_case = next(
        (
            row
            for row in rows
            if row.get("case_id") == "independent_equal_angle"
            and row.get("method") == "independent"
        ),
        None,
    )
    independent_hwp = next(
        (
            row
            for row in rows
            if row.get("case_id") == "independent_equal_angle"
            and row.get("method") == "hwp_adder_unitary"
        ),
        None,
    )
    weighted_hwp = next(
        (
            row
            for row in rows
            if row.get("case_id") == "weighted_triangle_free"
            and row.get("method") == "hwp_adder_unitary"
        ),
        None,
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"Across the selected rows, arithmetic contributes {arithmetic_total} T "
            f"gates and rotation synthesis contributes {rotation_total}; {dominant} "
            "is the larger reported component.",
            "",
        ]
    )
    if independent_case is not None and independent_hwp is not None:
        lines.extend(
            [
                "On `independent_equal_angle`, HWP changes T-count from "
                f"{independent_case['t_count']} to {independent_hwp['t_count']}, "
                f"T-depth from {independent_case['t_depth']} to "
                f"{independent_hwp['t_depth']}, and peak ancillas from "
                f"{independent_case['peak_workspace']} to "
                f"{independent_hwp['peak_workspace']}. Thus the T-count choice "
                "is not the T-depth or ancilla choice.",
                "",
            ]
        )
    if weighted_hwp is not None:
        lines.extend(
            [
                "On `weighted_triangle_free`, distinct coefficients prevent a "
                "multi-term equal-angle group. The HWP constructor records a "
                "direct fallback, so its zero-workspace row ties the direct "
                "references instead of demonstrating HWP applicability.",
                "",
            ]
        )
    lines.extend(
        [
            "An `adder_compressor_unitary_cap_1` choice is the HWP generator's "
            "zero-workspace direct fallback. Ancilla-first selections with that "
            "label therefore use the direct circuit, not collective arithmetic.",
            "",
            "Changing the objective does not generate another circuit. The policy "
            "columns select only among the evaluated rows; each HWP artifact also "
            "retains its evaluated batch variants and internal Pareto labels.",
            "",
            "The ordinary-HWP row is a unitary adaptation of the cited staged-adder "
            "construction. Reversing its arithmetic doubles the forward Toffoli "
            "cost relative to measurement-assisted cleanup. Measured and catalytic "
            "methods are unavailable here because their channel and resource-state "
            "obligations have not been implemented.",
            "",
            "The dependent-triple rule and the ANF popcount implementation are "
            "optional diagnostics, not default competitors. No novelty claim follows "
            "from selecting the cheapest existing circuit.",
            "",
            "## Research Decision",
            "",
            "This seven-case development study does not establish a recurring "
            "algorithmic limitation beyond ordinary HWP's expected equal-angle "
            "applicability boundary. The weighted negative control is one boundary "
            "example, not evidence for a new optimization mechanism.",
            "",
            "The next gated comparison is therefore implementation work rather than "
            "a novelty claim: emit and channel-verify the audited Gidney cleanup or "
            "Kan-Symons catalytic construction, include complete state preparation "
            "over matching repeated uses, and test whether it adds a nondominated "
            "point to this same fixed workload. If it does not, the hypothesis that "
            "measured or catalytic cleanup changes the observed frontier is falsified.",
            "",
        ]
    )
    return "\n".join(lines)
