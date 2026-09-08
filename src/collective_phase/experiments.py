from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time
from typing import Any, Callable

from .baselines import (
    compile_catalyzed_hwp,
    compile_hwp,
    compile_independent,
    compile_shared_parity,
)
from .baselines.common import CompilationConstraints
from .candidates import compile_dependent_triples
from .circuit import Candidate
from .inputs import acquire_manifest, load_cases, load_manifest
from .ir import AngleBinding, PhaseProgram
from .lowering import RotationSynthesizer, lower_candidate
from .profiles import StructuralProfile, profile
from .resources import estimate_resources
from .verification import verify_candidate, verify_dense_action


Compiler = Callable[[PhaseProgram, CompilationConstraints], Candidate]
COMPILERS: dict[str, Compiler] = {
    "independent": compile_independent,
    "shared_parity": compile_shared_parity,
    "hwp": compile_hwp,
    "catalyzed_hwp": compile_catalyzed_hwp,
    "dependent_triples": compile_dependent_triples,
}


def repository_root(config: dict[str, Any]) -> Path:
    return Path(config["_path"]).parent.parent


def config_hash(config: dict[str, Any]) -> str:
    public = {key: value for key, value in config.items() if not key.startswith("_")}
    data = json.dumps(public, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def _source_tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted((root / "src").rglob("*.py")) + [root / "pyproject.toml"]
    for path in paths:
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
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return commit + ("+dirty:" + _source_tree_hash(root)[:12] if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "source-tree-sha256:" + _source_tree_hash(root)


def _manifest_for_config(config: dict[str, Any]) -> dict[str, Any]:
    root = repository_root(config)
    return load_manifest(root / config["manifest"])


def acquire(config: dict[str, Any]) -> list[dict[str, str]]:
    return acquire_manifest(_manifest_for_config(config), repository_root(config))


def _angles(config: dict[str, Any]) -> list[AngleBinding]:
    return [AngleBinding(value["id"], str(value["value"])) for value in config["angles"]]


def audit_configuration(config: dict[str, Any]) -> dict[str, Any]:
    root = repository_root(config)
    manifest = _manifest_for_config(config)
    remote = [case for case in manifest["cases"] if "source_url" in case]
    missing = [case["local_path"] for case in remote if not (root / case["local_path"]).exists()]
    methods = list(config.get("methods", []))
    unknown = sorted(set(methods) - set(COMPILERS) - {"joint_synthesis"})
    synthesis_available = True
    synthesis_reason = None
    try:
        import pygridsynth  # noqa: F401
    except ImportError as exc:
        synthesis_available = False
        synthesis_reason = str(exc)
    return {
        "config": config["_path"],
        "config_hash": config_hash(config),
        "publication_mode": "undecided (implicit; no .research-repo.yml)",
        "git_worktree": (root / ".git").exists(),
        "case_count": len(manifest["cases"]),
        "remote_case_count": len(remote),
        "missing_remote_inputs": missing,
        "methods": methods,
        "unknown_methods": unknown,
        "generic_synthesis_available": synthesis_available,
        "generic_synthesis_reason": synthesis_reason,
        "semantic_profile": "diagonal P(theta), uncontrolled, exact angle IDs",
        "metric_profiles": config.get("model_profiles", []),
        "ready": not unknown and synthesis_available and not missing,
    }


def _profile_markdown(profiles: list[StructuralProfile], config: dict[str, Any]) -> str:
    lines = [
        "# Structural Diagnosis",
        "",
        f"Config hash: `{config_hash(config)}`",
        "",
        "This report is structural. Resource conclusions belong in the run report; rank alone is not treated as evidence of cheap integer accumulation.",
        "",
        "| Case | Terms | Unique | GF(2) rank | Dependencies | Triple coverage | Graph triangles |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in profiles:
        triangles = item.graph["triangle_count"] if item.graph else "n/a"
        lines.append(
            f"| {item.case_id} | {item.term_count} | {item.unique_parities} | "
            f"{item.binary_rank} | {len(item.dependency_witnesses)} | "
            f"{item.coverage_fraction:.3f} | {triangles} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The dependent-triple detector has a nonzero opportunity only where `Triple coverage` is nonzero. Duplicate multiplicities and complete graph details are retained in the adjacent JSON file. Weighted controls are expected to reject ordinary equal-angle HWP.",
            "",
        ]
    )
    return "\n".join(lines)


def profile_cases(config: dict[str, Any]) -> list[dict[str, Any]]:
    root = repository_root(config)
    manifest = _manifest_for_config(config)
    angle = _angles(config)[0]
    programs = load_cases(manifest, angle, root)
    profiles = [profile(program) for program in programs]
    output_path = root / config["diagnosis_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_profile_markdown(profiles, config), encoding="utf-8")
    json_path = output_path.with_suffix(".json")
    json_path.write_text(
        json.dumps([value.to_dict() for value in profiles], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return [value.to_dict() for value in profiles]


def _joint_unavailable(program: PhaseProgram, model_profile: str) -> Candidate:
    return Candidate(
        method="joint_synthesis",
        version="unavailable",
        program=program,
        status="unavailable",
        model_profile=model_profile,
        failure_reason=(
            "No verified NCF implementation with matching diagonal-block and operator-norm "
            "precision semantics is integrated"
        ),
    )


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _row_key(value: dict[str, Any]) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()[:24]


def run_experiments(config: dict[str, Any], force: bool = False) -> list[dict[str, Any]]:
    root = repository_root(config)
    manifest = _manifest_for_config(config)
    revision = code_revision(root)
    cfg_hash = config_hash(config)
    result_root = root / config["results_dir"]
    synthesizer = RotationSynthesizer(
        root / "results/generated/rotation-cache.json", seed=int(config.get("seed", 0))
    )
    rows: list[dict[str, Any]] = []
    for angle in _angles(config):
        programs = load_cases(manifest, angle, root)
        for program in programs:
            for total_error in config["total_error_budgets"]:
                for workspace in config["workspace_budgets"]:
                    for model_profile in config["model_profiles"]:
                        for method in config["methods"]:
                            reuse_counts = (
                                config.get("catalyst_reuse_counts", [1])
                                if method == "catalyzed_hwp"
                                else [1]
                            )
                            for reuse in reuse_counts:
                                identity = {
                                    "case_id": program.id,
                                    "angle_id": angle.id,
                                    "angle_expression": angle.expression,
                                    "error_budget": float(total_error),
                                    "workspace_budget": int(workspace),
                                    "model_profile": model_profile,
                                    "method": method,
                                    "reuse_count": int(reuse),
                                    "config_hash": cfg_hash,
                                    "code_commit": revision,
                                    "seed": int(config.get("seed", 0)),
                                }
                                row_id = _row_key(identity)
                                row_path = result_root / f"{row_id}.json"
                                if row_path.exists() and not force:
                                    rows.append(json.loads(row_path.read_text(encoding="utf-8")))
                                    continue
                                constraints = CompilationConstraints(
                                    workspace_budget=int(workspace),
                                    model_profile=model_profile,
                                    batch_policy=config.get("hwp_batch_policy", "balanced"),
                                    catalyst_reuse_count=int(reuse),
                                )
                                started = time.perf_counter()
                                if method == "joint_synthesis":
                                    candidate = _joint_unavailable(program, model_profile)
                                else:
                                    candidate = COMPILERS[method](program, constraints)
                                verification = verify_candidate(candidate)
                                row: dict[str, Any] = {
                                    **identity,
                                    "row_id": row_id,
                                    "source_hash": program.metadata["source_hash"],
                                    "status": candidate.status,
                                    "verification_status": verification.status,
                                    "error_metric": "operator_norm_telescoping",
                                    "error_bound": None,
                                    "t_count": None,
                                    "t_depth": None,
                                    "peak_workspace": candidate.workspace_qubits,
                                    "total_qubits": program.qubit_count + candidate.workspace_qubits,
                                    "clifford_count": None,
                                    "measurement_count": None,
                                    "adaptive_rounds": None,
                                    "preparation_t": None,
                                    "application_t": None,
                                    "compile_seconds": None,
                                    "circuit_path": None,
                                    "circuit_hash": None,
                                    "failure_reason": candidate.failure_reason,
                                    "accounting_status": candidate.accounting_status,
                                    "dense_error": None,
                                }
                                if candidate.status == "success" and verification.status in {
                                    "verified_exact",
                                    "verified_ideal_macro",
                                }:
                                    try:
                                        if program.qubit_count + candidate.workspace_qubits <= 10:
                                            row["dense_error"] = verify_dense_action(
                                                candidate, seed=int(config.get("seed", 0))
                                            )
                                        lowered = lower_candidate(candidate, float(total_error), synthesizer)
                                        resources = estimate_resources(lowered)
                                        row.update(resources.to_dict())
                                        row["error_bound"] = lowered.error_bound
                                        artifact = {
                                            "program": program.to_dict(),
                                            "candidate": candidate.to_dict(),
                                            "verification": verification.to_dict(),
                                            "rotations": {
                                                "application": [
                                                    value.to_dict()
                                                    for value in lowered.application_rotations
                                                ],
                                                "preparation": [
                                                    value.to_dict()
                                                    for value in lowered.preparation_rotations
                                                ],
                                            },
                                            "lowering": {
                                                "events": [asdict(event) for event in lowered.events],
                                                "global_phase": (
                                                    candidate.global_phase
                                                    + lowered.lowering_global_phase
                                                ),
                                                "error_metric": lowered.error_metric,
                                                "error_bound": lowered.error_bound,
                                            },
                                        }
                                        circuit_path = result_root / "circuits" / f"{row_id}.json"
                                        _atomic_json(circuit_path, artifact)
                                        row["circuit_path"] = str(circuit_path.relative_to(root))
                                        row["circuit_hash"] = hashlib.sha256(
                                            circuit_path.read_bytes()
                                        ).hexdigest()
                                    except Exception as exc:
                                        row["status"] = "synthesis_failure"
                                        row["failure_reason"] = str(exc)
                                elif candidate.status == "success":
                                    row["status"] = "verification_failure"
                                    row["failure_reason"] = verification.message
                                row["compile_seconds"] = time.perf_counter() - started
                                _atomic_json(row_path, row)
                                rows.append(row)
    return rows


def load_result_rows(results_path: str | Path) -> list[dict[str, Any]]:
    path = Path(results_path)
    return [
        json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(path.glob("*.json"))
        if item.is_file()
    ]


def verify_result_rows(results_path: str | Path, root: Path) -> dict[str, Any]:
    rows = load_result_rows(results_path)
    failures: list[str] = []
    for row in rows:
        if row["status"] != "success":
            continue
        expected_verification = (
            "verified_exact"
            if row["accounting_status"] == "emitted"
            else "verified_ideal_macro"
        )
        if row["verification_status"] != expected_verification:
            failures.append(
                f"{row['row_id']}: expected {expected_verification}, "
                f"got {row['verification_status']}"
            )
        if row["error_bound"] is None or row["error_bound"] > row["error_budget"] * (1 + 1e-7):
            failures.append(f"{row['row_id']}: invalid error bound")
        circuit_path = root / row["circuit_path"]
        if not circuit_path.exists():
            failures.append(f"{row['row_id']}: missing circuit artifact")
        elif hashlib.sha256(circuit_path.read_bytes()).hexdigest() != row["circuit_hash"]:
            failures.append(f"{row['row_id']}: circuit artifact checksum mismatch")
        if row.get("dense_error") is not None and row["dense_error"] > 1e-10:
            failures.append(f"{row['row_id']}: dense semantic check failed")
    return {
        "rows": len(rows),
        "successful_rows": sum(row["status"] == "success" for row in rows),
        "failures": failures,
        "status": "verified" if rows and not failures else "verification_failure",
        "scope": "stored semantic evidence, synthesis budgets, and artifact integrity",
    }


def render_report(rows: list[dict[str, Any]], results_path: Path) -> str:
    statuses = Counter(row["status"] for row in rows)
    successful = [row for row in rows if row["status"] == "success"]
    by_method: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in successful:
        by_method[(row["method"], row["accounting_status"])].append(row)
    lines = [
        "# Experiment Summary",
        "",
        f"Results: `{results_path}`",
        "",
        "This is prototype evidence, not a novelty or performance claim. Emitted and macro-estimated counts are separated.",
        "",
        "## Status",
        "",
    ]
    lines.extend(f"- `{status}`: {count}" for status, count in sorted(statuses.items()))
    lines.extend(
        [
            "",
            "## Resource overview",
            "",
            "| Method | Accounting | Rows | Mean T-count | Min T-count | Max T-count |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for (method, accounting), values in sorted(by_method.items()):
        counts = [int(value["t_count"]) for value in values]
        lines.append(
            f"| {method} | {accounting} | {len(values)} | "
            f"{statistics.fmean(counts):.2f} | {min(counts)} | {max(counts)} |"
        )

    paired: dict[tuple, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in successful:
        if row["reuse_count"] != 1:
            continue
        key = (
            row["case_id"],
            row["angle_id"],
            row["error_budget"],
            row["workspace_budget"],
            row["model_profile"],
        )
        paired[key][row["method"]] = row
    wins = ties = losses = 0
    ratios: list[float] = []
    for methods in paired.values():
        candidate = methods.get("dependent_triples")
        baselines = [
            methods[name]
            for name in ("independent", "shared_parity")
            if name in methods and methods[name]["accounting_status"] == "emitted"
        ]
        if candidate is None or candidate["accounting_status"] != "emitted" or not baselines:
            continue
        best = min(int(row["t_count"]) for row in baselines)
        value = int(candidate["t_count"])
        if value < best:
            wins += 1
        elif value == best:
            ties += 1
        else:
            losses += 1
        if best:
            ratios.append(value / best)
    lines.extend(
        [
            "",
            "## Candidate comparison",
            "",
            f"Against the best fully emitted independent/shared-parity baseline on paired unitary rows: {wins} wins, {ties} ties, {losses} losses.",
            (
                f"Mean paired T-count ratio: {statistics.fmean(ratios):.4f}."
                if ratios
                else "No nonzero paired ratio is available."
            ),
            "",
            "Catalyzed rows include preparation plus the declared number of applications. `amortized_t` divides total T-count by reuse count; composed T-depth is not amortized.",
            "",
            "## Four-part assessment",
            "",
            "- Observation: exact dependent triples occur in some diagnostics and graph triangles; HWP arithmetic cost is nonzero and separately reported.",
            "- Gap: this run does not establish that production HWP or joint-synthesis tools fail to recognize the same identity.",
            "- Verification: emitted rows passed exact basis checks; macro rows passed ideal-macro semantics only. Small coherent-state, per-rotation synthesis, and stored-artifact checks were applied where relevant.",
            "- Potential: continue only if generic-angle pilot wins survive stronger emitted HWP and NCF baselines on independently selected public cases.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(results_path: str | Path, output_path: str | Path | None = None) -> Path:
    path = Path(results_path)
    rows = load_result_rows(path)
    destination = Path(output_path) if output_path else path / "report.md"
    destination.write_text(render_report(rows, path), encoding="utf-8")
    return destination
