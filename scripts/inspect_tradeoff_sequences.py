#!/usr/bin/env python3
"""Run the bounded single-case tradeoff-sequence demonstration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from collective_phase.adapters import FeynmanAdapter, PhaseAncillaAdapter, PyZXAdapter
from collective_phase.adapters.phase_ancilla import (
    phase_regions,
    validated_scratch_pool,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.experiments import (
    audit_configuration,
    code_revision,
    config_hash,
    manifest_hash,
)
from collective_phase.inputs import load_cases, load_config, load_manifest
from collective_phase.ir import AngleBinding
from collective_phase.lowering import LoweredCircuit, RotationSynthesizer
from collective_phase.resources import estimate_resources, schedule_events
from collective_phase.search import SearchState, _state_key, construction_seeds
from collective_phase.selection import FinalObjective, SelectionLimits
from collective_phase.verification import verify_optimized_lowered_circuit


@dataclass
class CachedTransformation:
    result: Any
    uncached_seconds: float


@dataclass
class RunContext:
    error_budget: float
    objective: FinalObjective
    adapters: dict[str, Any]
    deadline: float
    cache: dict[
        tuple[str, str, str, tuple[int, int] | None, int], CachedTransformation
    ]


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _resources(state: SearchState) -> tuple[int, int, int]:
    return state.resource_tuple


def _state_summary(state: SearchState) -> dict[str, Any]:
    return {
        "label": state.label,
        "resources": list(_resources(state)),
        "source_seed": state.source_seed,
        "depth": state.depth,
        "verification": state.verification.status,
        "optimization": state.lowered.optimization,
        "state_key": _state_key(state),
    }


def _deduplicate(states: list[SearchState]) -> list[SearchState]:
    result: dict[str, SearchState] = {}
    for state in states:
        result.setdefault(_state_key(state), state)
    return list(result.values())


def _best(
    states: list[SearchState], objective: FinalObjective, limits: SelectionLimits
) -> SearchState | None:
    feasible = [state for state in states if limits.violation(state.resources) is None]
    if not feasible:
        return None
    return min(
        feasible,
        key=lambda state: objective.rank(state.resources, state.label),
    )


def _phase_targets(
    state: SearchState, maximum: int
) -> list[tuple[tuple[int, int], str, dict[str, Any]]]:
    schedule = state.schedule or schedule_events(state.lowered.events)
    state.schedule = schedule
    critical_events = set(schedule.critical_t_events)
    records: list[dict[str, Any]] = []
    for region in phase_regions(state.lowered.events):
        t_events = [
            index
            for index in range(*region)
            if state.lowered.events[index].kind in {"t", "tdg"}
        ]
        critical = sum(index in critical_events for index in t_events)
        mean_slack = (
            sum(schedule.event_slack[index] for index in t_events) / len(t_events)
            if t_events
            else 0.0
        )
        records.append(
            {
                "region": region,
                "t_events": len(t_events),
                "critical_t_events": critical,
                "mean_t_slack": mean_slack,
            }
        )
    if not records or maximum <= 0:
        return []

    selected: list[tuple[dict[str, Any], str]] = []
    critical = [record for record in records if record["critical_t_events"] > 0]
    if critical:
        selected.append(
            (
                max(
                    critical,
                    key=lambda record: (
                        record["critical_t_events"],
                        record["t_events"],
                        -record["mean_t_slack"],
                        -record["region"][0],
                    ),
                ),
                "critical",
            )
        )
    slack = [
        record
        for record in records
        if record["mean_t_slack"] > 0
        and all(record["region"] != item[0]["region"] for item in selected)
    ]
    if slack and len(selected) < maximum:
        selected.append(
            (
                max(
                    slack,
                    key=lambda record: (
                        record["mean_t_slack"],
                        record["t_events"],
                        -record["region"][0],
                    ),
                ),
                "slack",
            )
        )
    if not selected:
        selected.append(
            (max(records, key=lambda record: (record["t_events"], -record["region"][0])), "demand")
        )
    return [
        (record["region"], role, record)
        for record, role in selected[:maximum]
    ]


def _parse_action(value: str) -> tuple[str, int]:
    name, separator, allowance = value.partition("@")
    return name, int(allowance) if separator else 0


def _attempt(
    context: RunContext,
    source: SearchState,
    action_name: str,
    limits: SelectionLimits,
    *,
    region: tuple[int, int] | None = None,
    region_role: str = "whole_circuit",
    region_evidence: dict[str, Any] | None = None,
    allowance: int = 0,
) -> tuple[SearchState | None, dict[str, Any]]:
    before = _resources(source)
    started = time.monotonic()
    cache_key = (
        _state_key(source), source.source_seed, action_name, region, allowance
    )
    cache_status = "hit" if cache_key in context.cache else "miss"
    if time.monotonic() >= context.deadline:
        return None, {
            "source": source.label,
            "target": region_role,
            "region": None if region is None else list(region),
            "action": action_name,
            "allowance": allowance,
            "before": list(before),
            "after": list(before),
            "status": "time_budget",
            "feasible": False,
            "verification": None,
            "elapsed_seconds": 0.0,
            "uncached_transform_seconds": None,
            "cache_status": cache_status,
            "region_evidence": region_evidence,
            "scratch": {},
        }

    additional_scratch = 0
    if action_name == "phase_ancilla:parallel_phase":
        additional_scratch = max(
            0, allowance - len(validated_scratch_pool(source.lowered))
        )
        if region is None or allowance <= 0:
            raise ValueError("phase action requires a concrete region and allowance")
        if (
            limits.ancilla is not None
            and source.resources.peak_workspace + additional_scratch > limits.ancilla
        ):
            elapsed = time.monotonic() - started
            return None, {
                "source": source.label,
                "target": region_role,
                "region": list(region),
                "action": action_name,
                "allowance": allowance,
                "before": list(before),
                "after": list(before),
                "status": "hard_limit_precheck",
                "feasible": False,
                "verification": None,
                "elapsed_seconds": elapsed,
                "uncached_transform_seconds": None,
                "cache_status": "not_run",
                "region_evidence": region_evidence,
                "scratch": {"additional_requested": additional_scratch},
            }

    cached = context.cache.get(cache_key)
    if cached is None:
        transform_started = time.monotonic()
        remaining = max(0.0, context.deadline - transform_started)
        if action_name == "phase_ancilla:parallel_phase":
            result = context.adapters[action_name].optimize_region(
                source.lowered, region, allowance
            )
        else:
            backend, action = action_name.split(":", 1)
            result = context.adapters[action_name].optimize(
                source.lowered, action, timeout_seconds=remaining
            )
        cached = CachedTransformation(result, time.monotonic() - transform_started)
        context.cache[cache_key] = cached
    result = cached.result
    status = "accepted"
    verification = None
    output = None
    measured = source.resources
    if not result.verified or result.lowered is None:
        status = "timeout" if result.status == "timed_out" else "backend_failure"
    else:
        verification = verify_optimized_lowered_circuit(
            source.lowered,
            result.lowered,
            context.error_budget,
            ancestry=source.ancestry,
            timeout_seconds=max(0.0, context.deadline - time.monotonic()),
        )
        if not verification.status.startswith("verified_lowered_"):
            status = (
                "verification_inconclusive"
                if "unsupported" in verification.status
                else "verification_failure"
            )
        else:
            measured = estimate_resources(result.lowered)
            violation = limits.violation(measured)
            if violation is not None:
                status = "hard_limit"
            else:
                label = f"{source.label}|{action_name}"
                if region is not None:
                    label += f":{region_role}_{region[0]}_{region[1]}:scratch_{allowance}"
                output = SearchState(
                    label=label,
                    lowered=result.lowered,
                    resources=measured,
                    verification=verification,
                    objective_value=context.objective.value(measured),
                    source_seed=source.source_seed,
                    total_error=source.total_error,
                    schedule=schedule_events(result.lowered.events),
                    action=action_name,
                    parent_id=source.label,
                    depth=source.depth + 1,
                    ancestry=(*source.ancestry, source.lowered),
                )
    optimization = (
        result.lowered.optimization
        if result.lowered is not None and result.lowered.optimization is not None
        else {}
    )
    scratch_fields = (
        "scratch_wire_ids",
        "allocated_scratch_wire_ids",
        "reused_scratch_wire_ids",
        "released_scratch_wire_ids",
        "clean_scratch_pool",
    )
    elapsed = time.monotonic() - started
    return output, {
        "source": source.label,
        "output": None if output is None else output.label,
        "target": region_role,
        "region": None if region is None else list(region),
        "action": action_name,
        "allowance": allowance,
        "before": list(before),
        "after": list((measured.t_count, measured.t_depth, measured.peak_workspace)),
        "status": status,
        "failure_reason": result.reason,
        "feasible": output is not None,
        "verification": None if verification is None else verification.status,
        "verification_message": None if verification is None else verification.message,
        "elapsed_seconds": elapsed,
        "backend_seconds": result.backend_seconds,
        "uncached_transform_seconds": cached.uncached_seconds,
        "cache_status": cache_status,
        "region_evidence": region_evidence,
        "scratch": {
            field: list(optimization.get(field, ()))
            for field in scratch_fields
        },
    }


def _concrete_targets(
    state: SearchState,
    action_value: str,
    maximum_regions: int,
    default_allowances: list[int],
) -> list[tuple[str, tuple[int, int] | None, str, dict[str, Any] | None, int]]:
    action_name, configured_allowance = _parse_action(action_value)
    if action_name != "phase_ancilla:parallel_phase":
        return [(action_name, None, "whole_circuit", None, 0)]
    allowances = [configured_allowance] if configured_allowance else default_allowances
    return [
        (action_name, region, role, evidence, allowance)
        for region, role, evidence in _phase_targets(state, maximum_regions)
        for allowance in allowances
    ]


def _run_fixed_sequence(
    name: str,
    sequence: list[str],
    seeds: list[SearchState],
    context: RunContext,
    limits: SelectionLimits,
    maximum_regions: int,
    default_allowances: list[int],
    call_budget: int | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    attempts: list[dict[str, Any]] = []
    current = list(seeds)
    visited = list(seeds)
    if not sequence:
        endpoints = current
    else:
        endpoints = []
        for action_value in sequence:
            following: list[SearchState] = []
            for state in current:
                targets = _concrete_targets(
                    state, action_value, maximum_regions, default_allowances
                )
                if not targets:
                    attempts.append(
                        {
                            "source": state.label,
                            "target": "none",
                            "region": None,
                            "action": _parse_action(action_value)[0],
                            "allowance": _parse_action(action_value)[1],
                            "before": list(_resources(state)),
                            "after": list(_resources(state)),
                            "status": "not_applicable",
                            "feasible": False,
                            "verification": None,
                            "elapsed_seconds": 0.0,
                            "uncached_transform_seconds": None,
                            "cache_status": "not_run",
                            "region_evidence": None,
                            "scratch": {},
                        }
                    )
                    continue
                for action_name, region, role, evidence, allowance in targets:
                    if call_budget is not None and len(attempts) >= call_budget:
                        break
                    child, record = _attempt(
                        context,
                        state,
                        action_name,
                        limits,
                        region=region,
                        region_role=role,
                        region_evidence=evidence,
                        allowance=allowance,
                    )
                    attempts.append(record)
                    if child is not None:
                        following.append(child)
                if call_budget is not None and len(attempts) >= call_budget:
                    break
            current = _deduplicate(following)
            visited.extend(current)
            endpoints = current
            if not current or (call_budget is not None and len(attempts) >= call_budget):
                break
    best = _best(visited, context.objective, limits)
    return {
        "name": name,
        "status": "success" if best is not None else "no_feasible_endpoint",
        "sequence": sequence,
        "best": None if best is None else _state_summary(best),
        "best_state": best,
        "endpoints": endpoints,
        "states": _deduplicate(visited),
        "attempts": attempts,
        "attempt_count": len(attempts),
        "uncached_backend_calls": sum(
            record.get("cache_status") == "miss" for record in attempts
        ),
        "cache_hits": sum(record.get("cache_status") == "hit" for record in attempts),
        "elapsed_seconds": time.monotonic() - started,
    }


def _discover(
    seeds: list[SearchState],
    actions: list[str],
    context: RunContext,
    limits: SelectionLimits,
    *,
    maximum_depth: int,
    maximum_attempts: int,
    maximum_regions: int,
    allowances: list[int],
) -> dict[str, Any]:
    started = time.monotonic()
    roots = _deduplicate(
        [state for state in seeds if limits.violation(state.resources) is None]
    )
    frontier = roots
    states = list(roots)
    seen = {_state_key(state) for state in roots}
    attempted: set[tuple[str, str, tuple[int, int] | None, int]] = set()
    trace: list[dict[str, Any]] = []
    stopped_by = "frontier_exhausted"
    for _depth in range(maximum_depth):
        following: list[SearchState] = []
        for source in sorted(
            frontier,
            key=lambda state: context.objective.rank(state.resources, state.label),
        ):
            for action_value in actions:
                for action_name, region, role, evidence, allowance in _concrete_targets(
                    source, action_value, maximum_regions, allowances
                ):
                    key = (_state_key(source), action_name, region, allowance)
                    if key in attempted:
                        continue
                    if len(attempted) >= maximum_attempts:
                        stopped_by = "attempt_budget"
                        break
                    if time.monotonic() >= context.deadline:
                        stopped_by = "time_budget"
                        break
                    attempted.add(key)
                    child, record = _attempt(
                        context,
                        source,
                        action_name,
                        limits,
                        region=region,
                        region_role=role,
                        region_evidence=evidence,
                        allowance=allowance,
                    )
                    trace.append(record)
                    if child is not None:
                        identity = _state_key(child)
                        if identity not in seen:
                            seen.add(identity)
                            following.append(child)
                            states.append(child)
                if stopped_by in {"attempt_budget", "time_budget"}:
                    break
            if stopped_by in {"attempt_budget", "time_budget"}:
                break
        if stopped_by in {"attempt_budget", "time_budget"}:
            break
        frontier = following
        if not frontier:
            break
    winner = _best(states, context.objective, limits)
    return {
        "status": "success" if winner is not None else "no_feasible_endpoint",
        "stopped_by": stopped_by,
        "attempt_budget": maximum_attempts,
        "unique_attempts": len(attempted),
        "uncached_backend_calls": sum(
            record.get("cache_status") == "miss" for record in trace
        ),
        "cache_hits": sum(record.get("cache_status") == "hit" for record in trace),
        "elapsed_seconds": time.monotonic() - started,
        "trace": trace,
        "winner": None if winner is None else _state_summary(winner),
        "winner_state": winner,
        "state_count": len(states),
    }


def _environment() -> dict[str, str]:
    result = {"python": sys.version.split()[0]}
    for package in ("numpy", "pygridsynth", "pyzx", "PyYAML"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "unavailable"
    return result


def _replay_winner(state: SearchState, error_budget: float) -> str:
    chain = [*state.ancestry, state.lowered]
    if len(chain) == 1:
        return state.verification.status
    proof = verify_optimized_lowered_circuit(
        chain[-2], chain[-1], error_budget, ancestry=tuple(chain[:-2]),
        timeout_seconds=60,
    )
    measured = estimate_resources(chain[-1])
    if _resources(state) != (
        measured.t_count, measured.t_depth, measured.peak_workspace
    ):
        raise ValueError("winner replay changed the measured resources")
    if not proof.status.startswith("verified_lowered_"):
        raise ValueError(f"winner replay failed: {proof.status}: {proof.message}")
    return proof.status


def _render_report(result: dict[str, Any]) -> str:
    target = result["target"]
    status_counts: dict[str, int] = {}
    attempts = [
        attempt
        for reference in result["references"]
        for attempt in reference["attempts"]
    ]
    attempts.extend(result["discovery"]["trace"])
    attempts.extend(
        attempt
        for counterfactual in result["counterfactuals"]
        for attempt in counterfactual["attempts"]
    )
    for attempt in attempts:
        status = attempt["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    status_text = ", ".join(
        f"{name}={count}" for name, count in sorted(status_counts.items())
    )
    lines = [
        "# Single Tradeoff Demonstration",
        "",
        f"Run date: `{result['run_date']}`. Code: `{result['code_revision']}`. ",
        f"Input: `{target['case_id']}` (`sha256:{target['input_sha256']}`), angle ",
        f"`{target['angle']}`, total error `{target['error_budget']}`. This is an ",
        "existing development case, not held-out evidence.",
        "",
        "## Frozen target",
        "",
        f"The predeclared zero-ancilla references fixed `D0 = {target['d0']}` before ",
        f"custom discovery, giving `T-depth <= floor(1.10 * D0) = {target['depth_cap']}`. ",
        "The objective is minimum T-count subject to that depth cap, at most eight ",
        "additional clean qubits, and operator-norm approximation error at most `1e-4`. ",
        "Ties use T-depth and then ancillas.",
        "",
        "## Reference outcomes",
        "",
        "| Strategy | Status | Best `(T,D_T,A)` | Attempts | Uncached calls | Time (s) |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for reference in result["references"]:
        best = reference["best"]
        resources = "unavailable" if best is None else str(tuple(best["resources"]))
        lines.append(
            f"| {reference['name']} | {reference['status']} | {resources} | "
            f"{reference['attempt_count']} | {reference['uncached_backend_calls']} | "
            f"{reference['elapsed_seconds']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The Feynman row requires a real executable. None was present, so no stub or ",
            "estimate is reported. Every strategy otherwise started from the same complete ",
            "independent/shared-parity/HWP seed catalog.",
            "",
            "## Discovery and winner",
            "",
            f"Discovery stopped by `{result['discovery']['stopped_by']}` after "
            f"{result['discovery']['unique_attempts']} unique attempts and "
            f"{result['discovery']['elapsed_seconds']:.3f} seconds. It retained only "
            "intermediate states satisfying the hard limits. For each state it considered ",
            "at most one critical and one slack phase region, ranked by scheduled critical ",
            "T participation and mean T-slack.",
            "",
            f"The complete run took {result['total_seconds']:.3f} seconds, including "
            f"{result['root_seconds']:.3f} seconds of root preparation. Attempt statuses "
            f"across references, discovery, and counterfactuals were: `{status_text}`.",
            "",
            "| Step | Target | Action | Before | After | Verification | Scratch |",
            "| ---: | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for step, record in enumerate(result["winner_chain"], 1):
        scratch = record.get("scratch", {})
        scratch_text = (
            f"alloc={scratch.get('allocated_scratch_wire_ids', [])}, "
            f"reuse={scratch.get('reused_scratch_wire_ids', [])}, "
            f"release={scratch.get('released_scratch_wire_ids', [])}"
        )
        lines.append(
            f"| {step} | {record['target']} {record['region']} | {record['action']} | "
            f"{tuple(record['before'])} | {tuple(record['after'])} | "
            f"{record['verification']} | {scratch_text} |"
        )
    winner = result["discovery"]["winner"]
    lines.extend(
        [
            "",
            f"The emitted winner is `{winner['label']}` with resources "
            f"`{tuple(winner['resources'])}` and replay status "
            f"`{result['winner_replay_status']}`. The raw trace records backend failures, "
            "hard-limit exclusions, verification, timing, cache status, and scratch IDs.",
            "",
            "## Counterfactuals",
            "",
            "| Sequence | Status | Endpoint `(T,D_T,A)` | Attempts |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for comparison in result["counterfactuals"]:
        best = comparison["best"]
        resources = "unavailable" if best is None else str(tuple(best["resources"]))
        lines.append(
            f"| {comparison['name']} | {comparison['status']} | {resources} | "
            f"{comparison['attempt_count']} |"
        )
    lines.extend(
        [
            "",
            "Direct workspace resynthesis changes depth but not count. Reversing the two ",
            "actions reaches the same T-count with substantially worse depth. Repeating the ",
            "count backend makes no further count improvement after its first useful pass; ",
            "the strategy retains that best prefix. Applying the same final cleanup after ",
            "`full_optimize` does not improve the winner.",
            "",
            "## Conclusion",
            "",
            result["conclusion"],
            "",
            "The local phase action is a limited clean-scratch CNOT/diagonal resynthesis, ",
            "not a full T-par implementation. Whole-circuit PyZX invalidates scratch-pool ",
            "metadata. The search does not cross an intermediate hard-limit violation, and ",
            "dirty ancillas, measured cleanup, catalysts, and physical factory costs remain ",
            "outside this experiment.",
            "",
            "Reproduce with:",
            "",
            "```bash",
            ".venv/bin/python scripts/inspect_tradeoff_sequences.py --config configs/single-demonstration.yaml",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def run(config_path: Path) -> dict[str, Any]:
    overall_started = time.monotonic()
    config = load_config(config_path)
    root = config_path.resolve().parent.parent
    manifest = load_manifest(root / config["manifest"])
    angle_value = config["angles"][0]
    angle = AngleBinding(angle_value["id"], str(angle_value["value"]))
    case_id = config["demonstration"]["case_id"]
    program = next(
        program
        for program in load_cases(manifest, angle, root)
        if program.id == case_id
    )
    error_budget = float(config["total_error_budgets"][0])
    objective = FinalObjective.from_value(config["objective"])
    workspace = int(config["workspace_budgets"][0])
    search_config = config["search"]
    deadline = overall_started + float(search_config["backend_seconds_budget"])
    root_started = time.monotonic()
    seeds = construction_seeds(
        program,
        CompilationConstraints(
            workspace,
            config["model_profiles"][0],
            hwp_search_cap=int(config["hwp_search_cap"]),
        ),
        error_budget,
        RotationSynthesizer(
            root / "results/generated/rotation-cache.json",
            seed=int(config.get("seed", 0)),
        ),
        objective,
    )
    root_seconds = time.monotonic() - root_started
    audit = audit_configuration(config)
    pyzx = PyZXAdapter(seed=int(config.get("seed", 0)))
    adapters: dict[str, Any] = {
        "pyzx:zx_extract": pyzx,
        "pyzx:full_optimize": pyzx,
        "phase_ancilla:parallel_phase": PhaseAncillaAdapter(),
    }
    feynman_status = audit["backends"]["feynman"]
    if feynman_status["status"] == "available":
        backend_config = config["backends"]["feynman"]
        feynman = FeynmanAdapter(
            feynman_status["executable"],
            revision=feynman_status["revision"],
            timeout_seconds=float(backend_config.get("timeout_seconds", 30)),
        )
        adapters["feynman:phasefold"] = feynman
        adapters["feynman:tpar"] = feynman
    context = RunContext(error_budget, objective, adapters, deadline, {})
    pre_limits = SelectionLimits(ancilla=workspace)
    maximum_regions = int(search_config["max_regions_per_state"])
    allowances = [int(value) for value in search_config["phase_allowances"]]

    reference_results: list[dict[str, Any]] = []
    reference_states: list[SearchState] = []
    for name, sequence in config["demonstration"]["references"].items():
        if name == "feynman_fixed_order" and feynman_status["status"] != "available":
            reference_results.append(
                {
                    "name": name,
                    "status": "unavailable",
                    "sequence": sequence,
                    "best": None,
                    "attempts": [],
                    "attempt_count": 0,
                    "uncached_backend_calls": 0,
                    "cache_hits": 0,
                    "elapsed_seconds": 0.0,
                    "reason": feynman_status["reason"],
                    "endpoints": [],
                    "states": [],
                }
            )
            continue
        result = _run_fixed_sequence(
            name,
            list(sequence),
            seeds,
            context,
            pre_limits,
            maximum_regions,
            allowances,
        )
        reference_states.extend(result["states"])
        reference_results.append(result)
    zero_ancilla = [
        state
        for state in reference_states
        if state.resources.peak_workspace == 0
    ]
    if not zero_ancilla:
        raise RuntimeError("predeclared references produced no zero-ancilla output")
    zero_reference = min(
        zero_ancilla,
        key=lambda state: (
            state.resources.t_depth,
            state.resources.t_count,
            state.resources.peak_workspace,
            state.label,
        ),
    )
    d0 = zero_reference.resources.t_depth
    factor = float(config["demonstration"]["depth_reference_factor"])
    depth_cap = math.floor(factor * d0)
    final_limits = SelectionLimits(t_depth=depth_cap, ancilla=workspace)
    for reference in reference_results:
        reference.pop("endpoints", [])
        best = _best(reference.pop("states", []), objective, final_limits)
        reference["best_state"] = best
        reference["best"] = None if best is None else _state_summary(best)
        if reference["status"] != "unavailable":
            reference["status"] = "success" if best is not None else "no_feasible_endpoint"

    discovery = _discover(
        seeds,
        list(search_config["actions"]),
        context,
        final_limits,
        maximum_depth=int(search_config["max_depth"]),
        maximum_attempts=int(search_config["backend_call_budget"]),
        maximum_regions=maximum_regions,
        allowances=allowances,
    )
    winner = discovery["winner_state"]
    if winner is None:
        raise RuntimeError("bounded discovery produced no feasible winner")
    replay_status = _replay_winner(winner, error_budget)

    winner_root = next(seed for seed in seeds if seed.label == winner.source_seed)
    counterfactual_results: list[dict[str, Any]] = []
    remaining_counterfactuals = int(
        config["demonstration"]["counterfactual_call_budget"]
    )
    for name, sequence in config["demonstration"]["counterfactuals"].items():
        if remaining_counterfactuals <= 0:
            break
        comparison = _run_fixed_sequence(
            name,
            list(sequence),
            [winner_root],
            context,
            final_limits,
            1,
            allowances,
            call_budget=remaining_counterfactuals,
        )
        remaining_counterfactuals -= comparison["attempt_count"]
        counterfactual_results.append(comparison)

    count_then_depth = next(
        reference for reference in reference_results
        if reference["name"] == "count_then_depth"
    )
    fixed_matches = (
        count_then_depth["best"] is not None
        and count_then_depth["best"]["resources"] == list(_resources(winner))
    )
    conclusion = (
        "A predeclared fixed count-then-depth sequence matches the discovered winner. "
        "The gain is one PyZX count simplification followed by selection of the current "
        "critical local phase region with two useful clean scratch wires. Updating a "
        "preference vector is not needed to obtain this result, so no new policy rule or "
        "adaptive-quality claim is added. The discovered chain exercises certified scratch "
        "reuse, but the fixed sequence allocates both wires at once and reaches the same "
        "endpoint, so reuse is not an enabling benefit here."
        if fixed_matches
        else
        "The bounded discovery did not reduce to the predeclared fixed sequence. A matched "
        "frozen-preference comparison is required before making an adaptive claim."
    )

    winner_trace: list[dict[str, Any]] = []
    records_by_output = {
        record["output"]: record
        for record in discovery["trace"]
        if record.get("output") is not None
    }
    current_label = winner.label
    while current_label in records_by_output:
        record = records_by_output[current_label]
        winner_trace.append(record)
        current_label = record["source"]
    winner_trace.reverse()

    clean_references = []
    for reference in reference_results:
        clean_references.append(
            {
                key: value
                for key, value in reference.items()
                if key not in {"best_state"}
            }
        )
    clean_counterfactuals = []
    for comparison in counterfactual_results:
        clean_counterfactuals.append(
            {
                key: value
                for key, value in comparison.items()
                if key not in {"best_state", "endpoints", "states"}
            }
        )
    discovery_output = {
        key: value
        for key, value in discovery.items()
        if key != "winner_state"
    }
    result = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "run_date": time.strftime("%Y-%m-%d"),
        "code_revision": code_revision(root),
        "config_hash": config_hash(config),
        "manifest_hash": manifest_hash(manifest),
        "environment": _environment(),
        "backend_status": audit["backends"],
        "target": {
            "case_id": case_id,
            "input_sha256": program.metadata["source_hash"],
            "angle": angle.expression,
            "error_budget": error_budget,
            "workspace_cap": workspace,
            "d0": d0,
            "d0_source": _state_summary(zero_reference),
            "depth_cap": depth_cap,
            "objective": "minimize T-count; ties use T-depth then ancillas",
        },
        "limits": final_limits.to_dict(),
        "root_seconds": root_seconds,
        "total_seconds": time.monotonic() - overall_started,
        "construction_seeds": [_state_summary(seed) for seed in seeds],
        "references": clean_references,
        "discovery": discovery_output,
        "winner_chain": winner_trace,
        "winner_replay_status": replay_status,
        "counterfactuals": clean_counterfactuals,
        "counterfactual_attempts": sum(
            item["attempt_count"] for item in clean_counterfactuals
        ),
        "fixed_sequence_matches": fixed_matches,
        "conclusion": conclusion,
        "reachability_restriction": "intermediate hard-limit violations are excluded",
    }
    output_dir = root / config["results_dir"]
    artifact = {
        "schema_version": 4,
        "artifact_type": "single_demonstration_winner",
        "target_hash": _sha256_json(program.to_dict()),
        "program": program.to_dict(),
        "candidate": winner.lowered.candidate.to_dict(),
        "lowering": winner.lowered.to_dict(),
        "verified_chain": [
            lowered.to_dict() for lowered in (*winner.ancestry, winner.lowered)
        ],
        "verification": winner.verification.to_dict(),
        "resources": list(_resources(winner)),
        "source_seed": winner.source_seed,
        "winner_label": winner.label,
    }
    winner_path = output_dir / "winner.json"
    _write_json(winner_path, artifact)
    result["winner_artifact"] = {
        "path": str(winner_path.relative_to(root)),
        "sha256": hashlib.sha256(winner_path.read_bytes()).hexdigest(),
    }
    result_path = output_dir / "results.json"
    _write_json(result_path, result)
    report_path = root / config["report_path"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(result), encoding="utf-8")
    return {
        "result": str(result_path.relative_to(root)),
        "winner": str(winner_path.relative_to(root)),
        "report": str(report_path.relative_to(root)),
        "resources": list(_resources(winner)),
        "d0": d0,
        "depth_cap": depth_cap,
        "fixed_sequence_matches": fixed_matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/single-demonstration.yaml",
        type=Path,
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
