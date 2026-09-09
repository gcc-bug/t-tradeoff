from __future__ import annotations

from collections import Counter
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any

from .adapters import FeynmanAdapter, PyZXAdapter
from .baselines.common import CompilationConstraints
from .inputs import acquire_manifest, load_cases, load_manifest
from .ir import AngleBinding
from .lowering import RotationSynthesizer
from .preprocessing import PREPROCESSING_VERSION
from .profiles import StructuralProfile, profile
from .reporting import render_comparison_report
from .search import ActionSpec, construction_seeds, default_actions, run_policy
from .selection import FinalObjective, SelectionLimits


RESULT_SCHEMA_VERSION = 3
SEMANTIC_PROFILE = "diagonal-p-v1:block-local:operator-norm"
ERROR_METRIC = "operator_norm_telescoping"
POLICIES = frozenset(
    {
        "construction_only",
        "static_t",
        "static_depth",
        "static_ancilla",
        "static_balanced",
        "static_count_depth",
        "static_count_ancilla",
        "static_t_lookahead",
        "fixed_order",
        "adaptive",
        "adaptive_lookahead",
    }
)


def repository_root(config: dict[str, Any]) -> Path:
    return Path(config["_path"]).resolve().parent.parent


def _json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def config_hash(config: dict[str, Any]) -> str:
    return _json_hash(
        {key: value for key, value in config.items() if not key.startswith("_")}
    )


def _source_tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((root / "src").rglob("*.py")) + [root / "pyproject.toml"]:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def code_revision(root: Path) -> str:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "pyproject.toml"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return commit + (f"+dirty:{_source_tree_hash(root)[:12]}" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return f"source-tree-sha256:{_source_tree_hash(root)}"


def _manifest_for_config(config: dict[str, Any]) -> dict[str, Any]:
    return load_manifest(repository_root(config) / config["manifest"])


def manifest_hash(manifest: dict[str, Any]) -> str:
    return _json_hash(
        {key: value for key, value in manifest.items() if not key.startswith("_")}
    )


def acquire(config: dict[str, Any]) -> list[dict[str, str]]:
    return acquire_manifest(_manifest_for_config(config), repository_root(config))


def _angles(config: dict[str, Any]) -> list[AngleBinding]:
    return [AngleBinding(value["id"], str(value["value"])) for value in config["angles"]]


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def _feynman_status(config: dict[str, Any]) -> dict[str, Any]:
    backend = config.get("backends", {}).get("feynman", {})
    executable = str(backend.get("executable", "feynopt"))
    revision = str(backend.get("revision", "unconfigured"))
    resolved = shutil.which(executable)
    if resolved is None and not Path(executable).is_file():
        return {
            "status": "unsupported",
            "revision": revision,
            "reason": f"executable {executable!r} not found",
            "actions": [],
        }
    try:
        adapter = FeynmanAdapter(
            executable,
            revision=revision,
            timeout_seconds=float(backend.get("timeout_seconds", 30)),
        )
        actions = sorted(adapter.available_actions())
        return {
            "status": "available",
            "revision": revision,
            "executable": adapter.executable,
            "actions": actions,
        }
    except Exception as exc:
        return {
            "status": "unsupported",
            "revision": revision,
            "reason": str(exc),
            "actions": [],
        }


def audit_configuration(config: dict[str, Any]) -> dict[str, Any]:
    root = repository_root(config)
    manifest = _manifest_for_config(config)
    remote = [case for case in manifest["cases"] if "source_url" in case]
    missing = [
        case["local_path"]
        for case in remote
        if not (root / case["local_path"]).exists()
    ]
    errors: list[str] = []
    try:
        limits = SelectionLimits.from_value(config.get("limits"))
        objective = FinalObjective.from_value(config.get("objective", "t_count"))
        objective.validate_limits(limits)
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
        limits = None
        objective = None
    policies = list(config.get("policies", ["construction_only"]))
    unknown_policies = sorted(set(policies) - POLICIES)
    if unknown_policies:
        errors.append(f"unknown policies: {unknown_policies}")
    versions = {
        "python": platform.python_version(),
        "PyYAML": _version("PyYAML"),
        "numpy": _version("numpy"),
        "pygridsynth": _version("pygridsynth"),
        "pyzx": _version("pyzx"),
    }
    feynman = _feynman_status(config)
    executable = (
        not errors
        and not missing
        and all(versions[name] != "unavailable" for name in ("pygridsynth", "pyzx"))
    )
    return {
        "config": config["_path"],
        "config_hash": config_hash(config),
        "config_schema_version": config.get("schema_version"),
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "manifest_hash": manifest_hash(manifest),
        "code_revision": code_revision(root),
        "environment": versions,
        "case_count": len(manifest["cases"]),
        "strata": dict(
            Counter(case.get("stratum", "unclassified") for case in manifest["cases"])
        ),
        "missing_remote_inputs": missing,
        "policies": policies,
        "objective": None if objective is None else objective.to_dict(),
        "limits": None if limits is None else limits.to_dict(),
        "configuration_errors": errors,
        "backends": {
            "pyzx": {"status": "available", "revision": versions["pyzx"]},
            "feynman": feynman,
            "ncf": {"status": "unsupported", "reason": "no public artifact located"},
            "trasyn": {
                "status": "out_of_scope",
                "reason": "approximate resynthesis requires error reallocation",
            },
        },
        "semantic_profile": SEMANTIC_PROFILE,
        "preprocessing_version": PREPROCESSING_VERSION,
        "ready": executable,
        "basic_run_ready": executable,
    }


def _profile_markdown(values: list[StructuralProfile], config: dict[str, Any]) -> str:
    lines = [
        "# Structural Diagnosis",
        "",
        f"Config hash: `{config_hash(config)}`",
        "",
        "| Case | Terms | Unique | GF(2) rank | Dependencies |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for value in values:
        lines.append(
            f"| {value.case_id} | {value.term_count} | {value.unique_parities} | "
            f"{value.binary_rank} | {len(value.dependency_witnesses)} |"
        )
    return "\n".join(lines) + "\n"


def profile_cases(config: dict[str, Any]) -> list[dict[str, Any]]:
    root = repository_root(config)
    programs = load_cases(_manifest_for_config(config), _angles(config)[0], root)
    values = [profile(program) for program in programs]
    output = root / config["diagnosis_path"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_profile_markdown(values, config), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps([value.to_dict() for value in values], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return [value.to_dict() for value in values]


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _clear_checkpoints(result_root: Path, root: Path) -> None:
    resolved = result_root.resolve()
    results_root = (root / "results").resolve()
    if resolved == results_root or not resolved.is_relative_to(results_root):
        raise ValueError("forced result cleanup requires a subdirectory of results/")
    for path in result_root.glob("*.json"):
        path.unlink()
    for path in (result_root / "circuits").glob("*.json"):
        path.unlink()


def _actions(config: dict[str, Any]) -> tuple[list[ActionSpec], dict[str, Any]]:
    seed = int(config.get("seed", 0))
    pyzx = PyZXAdapter(seed=seed)
    status = _feynman_status(config)
    feynman = None
    if status["status"] == "available":
        backend = config.get("backends", {}).get("feynman", {})
        feynman = FeynmanAdapter(
            status["executable"],
            revision=status["revision"],
            timeout_seconds=float(backend.get("timeout_seconds", 30)),
        )
    actions = default_actions(pyzx, feynman)
    if feynman is not None:
        orientation = {
            "apf": (0.9, 0.3, 0.0),
            "qpf": (0.9, 0.3, 0.0),
            "ppf": (0.9, 0.3, 0.0),
        }
        requested = config.get("backends", {}).get("feynman", {}).get("actions", [])
        available = set(status["actions"])
        actions.extend(
            ActionSpec(f"feynman:{name}", "feynman", name, orientation[name], feynman)
            for name in requested
            if name in orientation and name in available
        )
    requested_names = config.get("search", {}).get("actions")
    if requested_names is not None:
        actions = [action for action in actions if action.name in requested_names]
    return actions, {
        "feynman": status,
        "ncf": {"status": "unsupported", "reason": "no public artifact located"},
        "pyzx": {"status": "available", "revision": "0.9.0"},
        "trasyn": {
            "status": "out_of_scope",
            "reason": "approximate resynthesis requires error reallocation",
        },
    }


def _policy_budget(policy: str, policies: list[str], search: dict[str, Any]) -> int:
    default = int(search.get("backend_call_budget", 4))
    weighted = [
        name
        for name in policies
        if name in {"static_balanced", "static_count_depth", "static_count_ancilla"}
    ]
    if policy not in weighted:
        return 0 if policy == "construction_only" else default
    position = weighted.index(policy)
    quotient, remainder = divmod(default, len(weighted))
    return quotient + int(position < remainder)


def _state_summary(state) -> dict[str, Any]:
    return {
        "label": state.label,
        "resources": list(state.resource_tuple),
        "objective_value": state.objective_value,
        "action": state.action,
        "source_seed": state.source_seed,
        "verification": state.verification.status,
        "optimization": state.lowered.optimization,
    }


def run_experiments(config: dict[str, Any], force: bool = False) -> list[dict[str, Any]]:
    root = repository_root(config)
    manifest = _manifest_for_config(config)
    objective = FinalObjective.from_value(config.get("objective", "t_count"))
    limits = SelectionLimits.from_value(config.get("limits"))
    objective.validate_limits(limits)
    policies = list(config.get("policies", ["construction_only"]))
    unknown = sorted(set(policies) - POLICIES)
    if unknown:
        raise ValueError(f"unknown policies: {unknown}")
    actions, backend_status = _actions(config)
    search_config = config.get("search", {})
    result_root = root / config["results_dir"]
    if force:
        _clear_checkpoints(result_root, root)
    revision = code_revision(root)
    cfg_hash = config_hash(config)
    input_hash = manifest_hash(manifest)
    synthesizer = RotationSynthesizer(
        root / "results/generated/rotation-cache.json",
        seed=int(config.get("seed", 0)),
    )
    rows: list[dict[str, Any]] = []
    for angle in _angles(config):
        for program in load_cases(manifest, angle, root):
            for total_error in config["total_error_budgets"]:
                for workspace in config["workspace_budgets"]:
                    for model_profile in config["model_profiles"]:
                        constraints = CompilationConstraints(
                            workspace_budget=int(workspace),
                            model_profile=model_profile,
                            batch_policy=str(config.get("hwp_batch_policy", "balanced")),
                            objective=objective.name,
                            hwp_search_cap=int(config.get("hwp_search_cap", 8)),
                        )
                        seeds = construction_seeds(
                            program,
                            constraints,
                            float(total_error),
                            synthesizer,
                            objective,
                        )
                        for policy in policies:
                            call_budget = _policy_budget(policy, policies, search_config)
                            identity = {
                                "case_id": program.id,
                                "target_hash": _json_hash(program.to_dict()),
                                "angle_id": angle.id,
                                "angle_expression": angle.expression,
                                "error_budget": float(total_error),
                                "workspace_budget": int(workspace),
                                "model_profile": model_profile,
                                "policy": policy,
                                "objective": objective.to_dict(),
                                "limits": limits.to_dict(),
                                "backend_call_budget": call_budget,
                                "backend_seconds_budget": float(
                                    search_config.get("backend_seconds_budget", 30)
                                ),
                                "config_hash": cfg_hash,
                                "manifest_hash": input_hash,
                                "code_revision": revision,
                                "seed": int(config.get("seed", 0)),
                            }
                            row_id = _json_hash(identity)[:24]
                            row_path = result_root / f"{row_id}.json"
                            if row_path.exists() and not force:
                                cached = json.loads(row_path.read_text(encoding="utf-8"))
                                if cached.get("schema_version") == RESULT_SCHEMA_VERSION:
                                    rows.append(cached)
                                    continue
                            result = run_policy(
                                seeds,
                                actions,
                                objective,
                                limits,
                                policy=policy,
                                max_backend_calls=call_budget,
                                max_backend_seconds=identity["backend_seconds_budget"],
                            )
                            selected = None if result.best is None else _state_summary(result.best)
                            row = {
                                **identity,
                                "schema_version": RESULT_SCHEMA_VERSION,
                                "row_id": row_id,
                                "semantic_profile": SEMANTIC_PROFILE,
                                "error_metric": ERROR_METRIC,
                                "preprocessing_version": PREPROCESSING_VERSION,
                                "stratum": program.metadata.get("stratum", "unclassified"),
                                "status": result.status,
                                "selected": selected,
                                "t_count": None if result.best is None else result.best.resources.t_count,
                                "t_depth": None if result.best is None else result.best.resources.t_depth,
                                "peak_workspace": None if result.best is None else result.best.resources.peak_workspace,
                                "objective_value": None if result.best is None else result.best.objective_value,
                                "verification_status": None if result.best is None else result.best.verification.status,
                                "error_bound": None if result.best is None else result.best.lowered.error_bound,
                                "evaluations": result.evaluations,
                                "backend_calls": result.backend_calls,
                                "backend_seconds": result.backend_seconds,
                                "trace": [value.to_dict() for value in result.trace],
                                "pareto": [
                                    _state_summary(value)
                                    for value in result.archive
                                    if value.label in result.pareto_labels
                                ],
                                "rejection_counts": result.rejection_counts,
                                "backend_status": backend_status,
                                "failure_reason": None,
                            }
                            artifact = {
                                "schema_version": RESULT_SCHEMA_VERSION,
                                "row_id": row_id,
                                "target_hash": identity["target_hash"],
                                "program": program.to_dict(),
                                "selected": selected,
                                "candidate": None if result.best is None else result.best.lowered.candidate.to_dict(),
                                "lowering": None if result.best is None else result.best.lowered.to_dict(),
                                "verification": None if result.best is None else result.best.verification.to_dict(),
                                "construction_seeds": [_state_summary(value) for value in seeds],
                                "archive": [_state_summary(value) for value in result.archive],
                            }
                            artifact_path = result_root / "circuits" / f"{row_id}.json"
                            _atomic_json(artifact_path, artifact)
                            row["artifact_path"] = str(artifact_path.relative_to(root))
                            row["artifact_hash"] = hashlib.sha256(
                                artifact_path.read_bytes()
                            ).hexdigest()
                            _atomic_json(row_path, row)
                            rows.append(row)
    return rows


def required_run_failures(
    rows: list[dict[str, Any]], config: dict[str, Any]
) -> list[str]:
    required = set(config.get("required_policies", config.get("policies", [])))
    return [
        f"{row['row_id']}: {row['policy']} status={row['status']}"
        for row in rows
        if row["policy"] in required and row["status"] != "success"
    ]


def load_result_rows(results_path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(Path(results_path).glob("*.json"))
    ]


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def verify_result_rows(results_path: str | Path, root: Path) -> dict[str, Any]:
    rows = load_result_rows(results_path)
    failures: list[str] = []
    root = root.resolve()
    for row in rows:
        row_id = row.get("row_id", "unknown")
        if row.get("schema_version") != RESULT_SCHEMA_VERSION:
            failures.append(f"{row_id}: unsupported result schema")
            continue
        if row.get("status") == "success":
            for name in (
                "t_count",
                "t_depth",
                "peak_workspace",
                "objective_value",
                "error_bound",
                "backend_seconds",
            ):
                if not _finite(row.get(name)) or row[name] < 0:
                    failures.append(f"{row_id}: invalid {name}")
            if row.get("error_bound", math.inf) > row.get("error_budget", 0) * (1 + 1e-7):
                failures.append(f"{row_id}: error budget exceeded")
            limits = SelectionLimits.from_value(row.get("limits"))
            checks = (
                ("t_count", limits.t_count),
                ("t_depth", limits.t_depth),
                ("peak_workspace", limits.ancilla),
            )
            for name, limit in checks:
                if limit is not None and row.get(name, math.inf) > limit:
                    failures.append(f"{row_id}: hard limit violated")
            if not str(row.get("verification_status", "")).startswith("verified_lowered_"):
                failures.append(f"{row_id}: selected circuit lacks verification")
        artifact_value = row.get("artifact_path")
        if not artifact_value:
            failures.append(f"{row_id}: missing artifact path")
            continue
        artifact_path = (root / artifact_value).resolve()
        if not artifact_path.is_relative_to(root) or not artifact_path.is_file():
            failures.append(f"{row_id}: invalid artifact path")
            continue
        if hashlib.sha256(artifact_path.read_bytes()).hexdigest() != row.get("artifact_hash"):
            failures.append(f"{row_id}: artifact checksum mismatch")
            continue
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        if artifact.get("row_id") != row_id:
            failures.append(f"{row_id}: artifact identity mismatch")
        if artifact.get("target_hash") != row.get("target_hash"):
            failures.append(f"{row_id}: target identity mismatch")
        if artifact.get("selected") != row.get("selected"):
            failures.append(f"{row_id}: selected summary mismatch")
    return {
        "rows": len(rows),
        "successful_rows": sum(row.get("status") == "success" for row in rows),
        "failures": failures,
        "status": "verified" if rows and not failures else "verification_failure",
        "scope": "schema-v3 row/artifact identity, checksums, limits, and recorded verification status",
    }


def render_report(rows: list[dict[str, Any]], results_path: Path) -> str:
    return render_comparison_report(rows, results_path)


def write_report(
    results_path: str | Path, output_path: str | Path | None = None
) -> Path:
    path = Path(results_path)
    destination = Path(output_path) if output_path else path / "report.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_report(load_result_rows(path), path), encoding="utf-8"
    )
    return destination
