from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import time
from typing import Any, Callable

from .baselines import (
    compile_catalyzed_hwp,
    compile_hwp_emitted_alternatives,
    compile_hwp_emitted_triple_grouped,
    compile_hwp_macro_legacy,
    compile_independent,
    compile_shared_parity,
)
from .baselines.common import CompilationConstraints
from .candidates import (
    compile_dependent_triples_raw,
    compile_hwp_dependency_simplified,
)
from .circuit import Candidate
from .inputs import acquire_manifest, load_cases, load_manifest
from .ir import AngleBinding, PhaseProgram
from .lowering import (
    LoweredCircuit,
    RotationSynthesizer,
    lower_candidate,
    lower_candidate_with_rotations,
)
from .preprocessing import PREPROCESSING_VERSION
from .profiles import StructuralProfile, profile
from .resources import ResourceRecord, characterize_tradeoff, estimate_resources
from .selection import SelectionResult, select_lowered_candidate
from .verification import (
    LoweredVerificationResult,
    VerificationResult,
    verify_candidate,
    verify_lowered_circuit,
)


RESULT_SCHEMA_VERSION = 2
SEMANTIC_PROFILE = "diagonal-p-v1:block-local:operator-norm"
ERROR_METRIC = "operator_norm_telescoping"
STRONG_BASELINES = (
    "hwp_emitted",
    "hwp_emitted_triple_grouped",
    "hwp_dependency_simplified",
)
BASIC_BASELINES = ("independent", "shared_parity")
PRIMARY_METHODS = {
    *STRONG_BASELINES,
    *BASIC_BASELINES,
    "dependent_triples_raw",
    "dependent_triples_selected",
}

Compiler = Callable[[PhaseProgram, CompilationConstraints], Candidate]
COMPILERS: dict[str, Compiler] = {
    "independent": compile_independent,
    "shared_parity": compile_shared_parity,
    "hwp_macro_legacy": compile_hwp_macro_legacy,
    "hwp_emitted_triple_grouped": compile_hwp_emitted_triple_grouped,
    "catalyzed_hwp_unverified": compile_catalyzed_hwp,
    "hwp_dependency_simplified": compile_hwp_dependency_simplified,
    "dependent_triples_raw": compile_dependent_triples_raw,
}
SPECIAL_METHODS = {"hwp_emitted", "dependent_triples_selected", "joint_synthesis"}


@dataclass
class ExecutedCandidate:
    candidate: Candidate
    ideal_verification: VerificationResult
    lowered: LoweredCircuit | None = None
    lowered_verification: LoweredVerificationResult | None = None
    resources: ResourceRecord | None = None
    alternatives: list[dict[str, Any]] | None = None


def repository_root(config: dict[str, Any]) -> Path:
    return Path(config["_path"]).parent.parent


def config_hash(config: dict[str, Any]) -> str:
    public = {key: value for key, value in config.items() if not key.startswith("_")}
    data = json.dumps(public, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def _json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


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
            [
                "git",
                "status",
                "--porcelain",
                "--",
                "src",
                "pyproject.toml",
            ],
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


def manifest_hash(manifest: dict[str, Any]) -> str:
    public = {
        key: value for key, value in manifest.items() if not key.startswith("_")
    }
    return _json_hash(public)


def acquire(config: dict[str, Any]) -> list[dict[str, str]]:
    return acquire_manifest(_manifest_for_config(config), repository_root(config))


def _angles(config: dict[str, Any]) -> list[AngleBinding]:
    return [AngleBinding(value["id"], str(value["value"])) for value in config["angles"]]


def _dependency_versions() -> dict[str, str]:
    result = {"python": platform.python_version()}
    for distribution in ("numpy", "pygridsynth", "PyYAML"):
        try:
            result[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            result[distribution] = "unavailable"
    return result


def audit_configuration(config: dict[str, Any]) -> dict[str, Any]:
    root = repository_root(config)
    manifest = _manifest_for_config(config)
    remote = [case for case in manifest["cases"] if "source_url" in case]
    missing = [
        case["local_path"]
        for case in remote
        if not (root / case["local_path"]).exists()
    ]
    methods = list(config.get("methods", []))
    unknown = sorted(set(methods) - set(COMPILERS) - SPECIAL_METHODS)
    versions = _dependency_versions()
    synthesis_available = versions["pygridsynth"] != "unavailable"
    executable = not unknown and synthesis_available and not missing
    strong_methods = sorted(set(methods) & set(STRONG_BASELINES))
    return {
        "config": config["_path"],
        "config_schema_version": config.get("schema_version"),
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "config_hash": config_hash(config),
        "manifest_hash": manifest_hash(manifest),
        "starting_revision": "32ad1131eb16eabdeb04d75fd4b90f344ea0c7e9",
        "code_revision": code_revision(root),
        "environment": versions,
        "publication_mode": "undecided/double-blind safeguards required",
        "canonical_remote_is_identifying": True,
        "git_worktree": (root / ".git").exists(),
        "case_count": len(manifest["cases"]),
        "strata": dict(
            Counter(case.get("stratum", "unclassified") for case in manifest["cases"])
        ),
        "remote_case_count": len(remote),
        "missing_remote_inputs": missing,
        "methods": methods,
        "unknown_methods": unknown,
        "generic_synthesis_available": synthesis_available,
        "semantic_profile": SEMANTIC_PROFILE,
        "preprocessing_version": PREPROCESSING_VERSION,
        "metric_profiles": config.get("model_profiles", []),
        "analysis_focus": config.get(
            "analysis_focus", "fully_lowered_resource_outcomes"
        ),
        "basic_run_ready": executable,
        "strong_comparison_methods": strong_methods,
        "strong_comparison_ready": executable and bool(strong_methods),
        "measured_catalytic_primary_ready": False,
        "ready": executable,
    }


def _profile_markdown(
    profiles: list[StructuralProfile], config: dict[str, Any]
) -> str:
    lines = [
        "# Structural Diagnosis",
        "",
        f"Config hash: {config_hash(config)}",
        "",
        "This report is structural. Resource conclusions belong in the run report.",
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
            "Dependent-triple coverage identifies only where the raw rule can run. "
            "It is not a resource advantage until full lowering and the "
            "dependency-simplified HWP overlap test pass.",
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
    output_path.with_suffix(".json").write_text(
        json.dumps([value.to_dict() for value in profiles], indent=2, sort_keys=True)
        + "\n",
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
            "No verified joint-synthesis implementation with matching diagonal-block "
            "and operator-norm precision semantics is integrated"
        ),
        accounting_status="unavailable",
        implementation_family="joint_synthesis",
        variant="unavailable",
        preprocessing_version=PREPROCESSING_VERSION,
    )


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _row_key(value: dict[str, Any]) -> str:
    return _json_hash(value)[:24]


def _operation_signature(candidate: Candidate) -> str:
    return _json_hash(
        {
            "operations": [
                operation.to_dict() for operation in candidate.operations
            ],
            "workspace_qubits": candidate.workspace_qubits,
            "global_phase": candidate.global_phase,
        }
    )


def _execute_method(
    method: str,
    program: PhaseProgram,
    constraints: CompilationConstraints,
    total_error: float,
    synthesizer: RotationSynthesizer,
) -> ExecutedCandidate:
    selection: SelectionResult | None = None
    if method == "hwp_emitted":
        selection = select_lowered_candidate(
            compile_hwp_emitted_alternatives(program, constraints),
            total_error,
            synthesizer,
            selected_method="hwp_emitted",
            objective=constraints.objective,
        )
    elif method == "dependent_triples_selected":
        selection = select_lowered_candidate(
            [
                compile_dependent_triples_raw(program, constraints),
                compile_independent(program, constraints),
                compile_shared_parity(program, constraints),
            ],
            total_error,
            synthesizer,
            selected_method="dependent_triples_selected",
            objective=constraints.objective,
            preferred_method="dependent_triples_raw",
        )
    if selection is not None:
        lowered_verification = verify_lowered_circuit(
            selection.lowered, total_error
        )
        return ExecutedCandidate(
            candidate=selection.candidate,
            ideal_verification=verify_candidate(selection.candidate),
            lowered=selection.lowered,
            lowered_verification=lowered_verification,
            resources=estimate_resources(selection.lowered),
            alternatives=[
                item.artifact() for item in selection.alternatives
            ],
        )

    if method == "joint_synthesis":
        candidate = _joint_unavailable(program, constraints.model_profile)
    else:
        candidate = COMPILERS[method](program, constraints)
    ideal = verify_candidate(candidate)
    executed = ExecutedCandidate(candidate, ideal)
    expected_ideal = (
        "verified_ideal_semantics"
        if candidate.accounting_status == "emitted"
        else "verified_ideal_macro_semantics"
    )
    if candidate.status != "success" or ideal.status != expected_ideal:
        return executed
    lowered = lower_candidate(candidate, total_error, synthesizer)
    executed.lowered = lowered
    executed.lowered_verification = verify_lowered_circuit(
        lowered, total_error
    )
    executed.resources = estimate_resources(lowered)
    return executed


def _base_row(
    identity: dict[str, Any], program: PhaseProgram
) -> dict[str, Any]:
    return {
        **identity,
        "schema_version": RESULT_SCHEMA_VERSION,
        "row_id": _row_key(identity),
        "target_hash": _json_hash(program.to_dict()),
        "source_hash": program.metadata["source_hash"],
        "stratum": program.metadata.get("stratum", "unclassified"),
        "status": "not_run",
        "implementation_family": None,
        "variant": None,
        "selected_from": None,
        "selected_construction": None,
        "used_rewrite": False,
        "matched_triples": 0,
        "accounting_status": None,
        "primary_eligible": False,
        "ideal_verification_status": "not_run",
        "lowered_verification_status": "not_run",
        "verification_scope": "not_run",
        "operator_norm_error": None,
        "error_bound": None,
        "t_count": None,
        "t_depth": None,
        "peak_workspace": None,
        "total_qubits": None,
        "clifford_count": None,
        "measurement_count": None,
        "adaptive_rounds": None,
        "preparation_t": None,
        "application_t": None,
        "application_rotations": None,
        "generic_application_rotations": None,
        "exact_application_rotations": None,
        "preparation_rotations": None,
        "generic_preparation_rotations": None,
        "exact_preparation_rotations": None,
        "logical_toffoli_count": None,
        "logical_cx_count": None,
        "logical_x_count": None,
        "compile_seconds": None,
        "circuit_path": None,
        "circuit_hash": None,
        "operation_signature": None,
        "failure_reason": None,
    }


def run_experiments(
    config: dict[str, Any], force: bool = False
) -> list[dict[str, Any]]:
    root = repository_root(config)
    manifest = _manifest_for_config(config)
    revision = code_revision(root)
    cfg_hash = config_hash(config)
    input_manifest_hash = manifest_hash(manifest)
    result_root = root / config["results_dir"]
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
                        for method in config["methods"]:
                            reuse_counts = (
                                config.get("catalyst_reuse_counts", [1])
                                if method
                                in {
                                    "catalyzed_hwp",
                                    "catalyzed_hwp_unverified",
                                }
                                else [1]
                            )
                            for reuse in reuse_counts:
                                objective = config.get(
                                    "objective", "t_count"
                                )
                                identity = {
                                    "result_schema_version": RESULT_SCHEMA_VERSION,
                                    "case_id": program.id,
                                    "target_hash": _json_hash(
                                        program.to_dict()
                                    ),
                                    "semantic_profile": SEMANTIC_PROFILE,
                                    "preprocessing_version": PREPROCESSING_VERSION,
                                    "angle_id": angle.id,
                                    "angle_expression": angle.expression,
                                    "error_budget": float(total_error),
                                    "error_metric": ERROR_METRIC,
                                    "workspace_budget": int(workspace),
                                    "model_profile": model_profile,
                                    "method": method,
                                    "reuse_count": int(reuse),
                                    "objective": objective,
                                    "analysis_focus": config.get(
                                        "analysis_focus",
                                        "fully_lowered_resource_outcomes",
                                    ),
                                    "config_hash": cfg_hash,
                                    "manifest_hash": input_manifest_hash,
                                    "code_revision": revision,
                                    "seed": int(config.get("seed", 0)),
                                }
                                row_id = _row_key(identity)
                                row_path = result_root / f"{row_id}.json"
                                if row_path.exists() and not force:
                                    cached = json.loads(
                                        row_path.read_text(
                                            encoding="utf-8"
                                        )
                                    )
                                    if (
                                        cached.get("schema_version")
                                        == RESULT_SCHEMA_VERSION
                                    ):
                                        rows.append(cached)
                                        continue
                                row = _base_row(identity, program)
                                started = time.perf_counter()
                                try:
                                    constraints = CompilationConstraints(
                                        workspace_budget=int(workspace),
                                        model_profile=model_profile,
                                        batch_policy=config.get(
                                            "hwp_batch_policy", "balanced"
                                        ),
                                        catalyst_reuse_count=int(reuse),
                                        objective=objective,
                                        hwp_search_cap=int(
                                            config.get(
                                                "hwp_search_cap", 8
                                            )
                                        ),
                                    )
                                    executed = _execute_method(
                                        method,
                                        program,
                                        constraints,
                                        float(total_error),
                                        synthesizer,
                                    )
                                    candidate = executed.candidate
                                    row.update(
                                        {
                                            "status": candidate.status,
                                            "implementation_family": candidate.implementation_family,
                                            "variant": candidate.variant,
                                            "selected_from": candidate.selected_from,
                                            "selected_construction": (
                                                candidate.selected_from
                                                or candidate.variant
                                            ),
                                            "used_rewrite": bool(
                                                candidate.parameters.get(
                                                    "used_rewrite", False
                                                )
                                            ),
                                            "matched_triples": int(
                                                candidate.parameters.get(
                                                    "matched_triples", 0
                                                )
                                            ),
                                            "accounting_status": candidate.accounting_status,
                                            "ideal_verification_status": executed.ideal_verification.status,
                                            "peak_workspace": candidate.workspace_qubits,
                                            "total_qubits": (
                                                program.qubit_count
                                                + candidate.workspace_qubits
                                            ),
                                            "operation_signature": _operation_signature(
                                                candidate
                                            ),
                                            "failure_reason": candidate.failure_reason,
                                        }
                                    )
                                    if (
                                        candidate.status == "success"
                                        and executed.lowered is not None
                                    ):
                                        assert executed.resources is not None
                                        assert (
                                            executed.lowered_verification
                                            is not None
                                        )
                                        lowered_status = (
                                            executed.lowered_verification.status
                                        )
                                        emitted_ok = lowered_status.startswith(
                                            "verified_lowered_"
                                        )
                                        if (
                                            candidate.accounting_status
                                            == "emitted"
                                            and not emitted_ok
                                        ):
                                            row["status"] = (
                                                "verification_failure"
                                            )
                                            row["failure_reason"] = (
                                                executed.lowered_verification.message
                                            )
                                        else:
                                            row.update(
                                                executed.resources.to_dict()
                                            )
                                            tradeoff = characterize_tradeoff(
                                                executed.lowered
                                            )
                                            row.update(tradeoff.to_dict())
                                            row["error_bound"] = (
                                                executed.lowered.error_bound
                                            )
                                            row[
                                                "lowered_verification_status"
                                            ] = lowered_status
                                            row["verification_scope"] = (
                                                executed.lowered_verification.scope
                                            )
                                            row["operator_norm_error"] = (
                                                executed.lowered_verification.operator_norm_error
                                            )
                                            row["primary_eligible"] = (
                                                method in PRIMARY_METHODS
                                                and candidate.accounting_status
                                                == "emitted"
                                                and emitted_ok
                                            )
                                            artifact = {
                                                "schema_version": RESULT_SCHEMA_VERSION,
                                                "target_hash": row[
                                                    "target_hash"
                                                ],
                                                "manifest_hash": row[
                                                    "manifest_hash"
                                                ],
                                                "program": program.to_dict(),
                                                "candidate": candidate.to_dict(),
                                                "ideal_verification": executed.ideal_verification.to_dict(),
                                                "lowered_verification": executed.lowered_verification.to_dict(),
                                                "lowering": executed.lowered.to_dict(),
                                                "resources": executed.resources.to_dict(),
                                                "tradeoff": tradeoff.to_dict(),
                                                "alternatives": (
                                                    executed.alternatives
                                                    or []
                                                ),
                                            }
                                            circuit_path = (
                                                result_root
                                                / "circuits"
                                                / f"{row_id}.json"
                                            )
                                            _atomic_json(
                                                circuit_path, artifact
                                            )
                                            row["circuit_path"] = str(
                                                circuit_path.relative_to(root)
                                            )
                                            row["circuit_hash"] = (
                                                hashlib.sha256(
                                                    circuit_path.read_bytes()
                                                ).hexdigest()
                                            )
                                    elif candidate.status == "success":
                                        row["status"] = (
                                            "verification_failure"
                                        )
                                        row["failure_reason"] = (
                                            executed.ideal_verification.message
                                        )
                                except Exception as exc:
                                    row["status"] = "execution_failure"
                                    row["failure_reason"] = str(exc)
                                row["compile_seconds"] = (
                                    time.perf_counter() - started
                                )
                                _atomic_json(row_path, row)
                                rows.append(row)
    return rows


def required_run_failures(
    rows: list[dict[str, Any]], config: dict[str, Any]
) -> list[str]:
    required = set(
        config.get(
            "required_methods",
            [
                method
                for method in config.get("methods", [])
                if method
                not in {
                    "joint_synthesis",
                    "hwp_macro_legacy",
                    "catalyzed_hwp_unverified",
                }
            ],
        )
    )
    failures = []
    for row in rows:
        if row["method"] not in required:
            continue
        if row["status"] != "success":
            failures.append(
                f"{row['row_id']}: {row['method']} status={row['status']}"
            )
        elif (
            row["method"] in PRIMARY_METHODS
            and not row.get("primary_eligible", False)
        ):
            failures.append(
                f"{row['row_id']}: {row['method']} lacks emitted verification"
            )
    return failures


def load_result_rows(
    results_path: str | Path,
) -> list[dict[str, Any]]:
    path = Path(results_path)
    return [
        json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(path.glob("*.json"))
        if item.is_file()
    ]


def _finite_number(value: Any, *, nonnegative: bool = True) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and (not nonnegative or value >= 0)
    )


def _verify_lowering_artifact(
    prefix: str,
    candidate: Candidate,
    lowering_value: dict[str, Any],
    total_error: float,
    stored_resources: dict[str, Any] | None,
) -> tuple[
    list[str],
    LoweredCircuit | None,
    ResourceRecord | None,
    LoweredVerificationResult | None,
]:
    failures: list[str] = []
    try:
        stored = LoweredCircuit.from_dict(lowering_value, candidate)
        replayed = lower_candidate_with_rotations(
            candidate,
            total_error,
            stored.application_rotations,
            stored.preparation_rotations,
        )
        if replayed.to_dict() != lowering_value:
            failures.append(
                f"{prefix}: stored gate stream does not match replayed lowering"
            )
        verification = verify_lowered_circuit(stored, total_error)
        resources = estimate_resources(stored)
        if (
            stored_resources is not None
            and resources.to_dict() != stored_resources
        ):
            failures.append(
                f"{prefix}: stored artifact resources do not recompute"
            )
        return failures, stored, resources, verification
    except Exception as exc:
        failures.append(f"{prefix}: lowering replay failed: {exc}")
        return failures, None, None, None


def verify_result_rows(
    results_path: str | Path, root: Path
) -> dict[str, Any]:
    rows = load_result_rows(results_path)
    failures: list[str] = []
    replayed_successes = 0
    for row in rows:
        row_id = row.get("row_id", "unknown-row")
        if row.get("schema_version") != RESULT_SCHEMA_VERSION:
            failures.append(
                f"{row_id}: unsupported result schema; "
                "excluded from primary evidence"
            )
            continue
        if not _finite_number(row.get("compile_seconds")):
            failures.append(f"{row_id}: invalid compile_seconds")
        if row.get("status") != "success":
            continue
        for field in (
            "error_budget",
            "error_bound",
            "t_count",
            "t_depth",
            "peak_workspace",
            "total_qubits",
            "measurement_count",
            "adaptive_rounds",
            "preparation_t",
            "application_t",
            "preparation_depth",
            "application_depth",
            "application_rotations",
            "generic_application_rotations",
            "exact_application_rotations",
            "preparation_rotations",
            "generic_preparation_rotations",
            "exact_preparation_rotations",
            "logical_toffoli_count",
            "logical_cx_count",
            "logical_x_count",
            "reuse_count",
            "amortized_t",
        ):
            if not _finite_number(row.get(field)):
                failures.append(f"{row_id}: invalid {field}")
        if row.get("error_bound", math.inf) > row.get(
            "error_budget", 0
        ) * (1 + 1e-7):
            failures.append(
                f"{row_id}: synthesis-error budget exceeded"
            )
        circuit_path_value = row.get("circuit_path")
        if not circuit_path_value:
            failures.append(f"{row_id}: missing circuit artifact path")
            continue
        circuit_path = root / circuit_path_value
        if not circuit_path.exists():
            failures.append(f"{row_id}: missing circuit artifact")
            continue
        actual_hash = hashlib.sha256(circuit_path.read_bytes()).hexdigest()
        if actual_hash != row.get("circuit_hash"):
            failures.append(
                f"{row_id}: circuit artifact checksum mismatch"
            )
        try:
            artifact = json.loads(
                circuit_path.read_text(encoding="utf-8")
            )
            if artifact.get("schema_version") != RESULT_SCHEMA_VERSION:
                raise ValueError("unsupported artifact schema")
            program = PhaseProgram.from_dict(artifact["program"])
            target_hash = _json_hash(program.to_dict())
            if (
                target_hash != row.get("target_hash")
                or target_hash != artifact.get("target_hash")
            ):
                failures.append(f"{row_id}: target identity mismatch")
            if row.get("manifest_hash") != artifact.get("manifest_hash"):
                failures.append(f"{row_id}: manifest identity mismatch")
            if program.id != row.get("case_id"):
                failures.append(f"{row_id}: case identity mismatch")
            if (
                program.metadata.get("source_hash")
                != row.get("source_hash")
            ):
                failures.append(f"{row_id}: source hash mismatch")
            candidate = Candidate.from_dict(
                artifact["candidate"], program
            )
            for key in (
                "method",
                "variant",
                "implementation_family",
                "selected_from",
                "accounting_status",
                "preprocessing_version",
            ):
                if getattr(candidate, key) != row.get(key):
                    failures.append(
                        f"{row_id}: candidate {key} mismatch"
                    )
            if _operation_signature(candidate) != row.get(
                "operation_signature"
            ):
                failures.append(
                    f"{row_id}: operation signature mismatch"
                )
            ideal = verify_candidate(candidate)
            if ideal.to_dict() != artifact.get("ideal_verification"):
                failures.append(
                    f"{row_id}: ideal verification evidence "
                    "does not recompute"
                )
            if ideal.status != row.get("ideal_verification_status"):
                failures.append(
                    f"{row_id}: ideal verification status mismatch"
                )
            (
                lowering_failures,
                lowered,
                resources,
                lowered_verification,
            ) = _verify_lowering_artifact(
                row_id,
                candidate,
                artifact["lowering"],
                float(row["error_budget"]),
                artifact.get("resources"),
            )
            failures.extend(lowering_failures)
            if (
                lowered is not None
                and resources is not None
                and lowered_verification is not None
            ):
                for key, value in resources.to_dict().items():
                    if row.get(key) != value:
                        failures.append(
                            f"{row_id}: row resource {key} "
                            "does not recompute"
                        )
                tradeoff = characterize_tradeoff(lowered)
                if tradeoff.to_dict() != artifact.get("tradeoff"):
                    failures.append(
                        f"{row_id}: stored artifact tradeoff does not recompute"
                    )
                for key, value in tradeoff.to_dict().items():
                    if row.get(key) != value:
                        failures.append(
                            f"{row_id}: row tradeoff {key} does not recompute"
                        )
                expected_matched = int(
                    candidate.parameters.get("matched_triples", 0)
                )
                if row.get("matched_triples") != expected_matched:
                    failures.append(
                        f"{row_id}: matched triple count does not recompute"
                    )
                if row.get("error_bound") != lowered.error_bound:
                    failures.append(
                        f"{row_id}: row error bound does not recompute"
                    )
                if (
                    lowered_verification.to_dict()
                    != artifact.get("lowered_verification")
                ):
                    failures.append(
                        f"{row_id}: lowered verification evidence "
                        "does not recompute"
                    )
                if lowered_verification.status != row.get(
                    "lowered_verification_status"
                ):
                    failures.append(
                        f"{row_id}: lowered verification status mismatch"
                    )
                emitted_ok = lowered_verification.status.startswith(
                    "verified_lowered_"
                )
                if (
                    candidate.accounting_status == "emitted"
                    and not emitted_ok
                ):
                    failures.append(
                        f"{row_id}: emitted row lacks lowered verification"
                    )
                expected_primary = (
                    row.get("method") in PRIMARY_METHODS
                    and candidate.accounting_status == "emitted"
                    and emitted_ok
                )
                if row.get("primary_eligible") != expected_primary:
                    failures.append(
                        f"{row_id}: primary eligibility mismatch"
                    )
                if expected_primary and not _finite_number(
                    row.get("clifford_count")
                ):
                    failures.append(
                        f"{row_id}: emitted row has invalid clifford_count"
                    )
            replayed_alternatives: list[dict[str, Any]] = []
            for index, alternative in enumerate(
                artifact.get("alternatives", [])
            ):
                alternative_candidate = Candidate.from_dict(
                    alternative["candidate"], program
                )
                alternative_ideal = verify_candidate(alternative_candidate)
                if alternative_ideal.to_dict() != alternative.get(
                    "ideal_verification_evidence"
                ):
                    failures.append(
                        f"{row_id}:alternative:{index}: ideal evidence "
                        "does not recompute"
                    )
                lowering = alternative.get("lowering")
                if lowering is None:
                    replayed_alternatives.append(
                        {
                            "label": alternative["label"],
                            "eligible": False,
                            "resource_tuple": None,
                            "operation_signature": _operation_signature(
                                alternative_candidate
                            ),
                        }
                    )
                    continue
                (
                    alternative_failures,
                    alternative_lowered,
                    alternative_resources,
                    alternative_verification,
                ) = _verify_lowering_artifact(
                    f"{row_id}:alternative:{index}",
                    alternative_candidate,
                    lowering,
                    float(row["error_budget"]),
                    alternative.get("resources"),
                )
                failures.extend(alternative_failures)
                if alternative_lowered is not None:
                    alternative_tradeoff = characterize_tradeoff(
                        alternative_lowered
                    ).to_dict()
                    if alternative.get("tradeoff") != alternative_tradeoff:
                        failures.append(
                            f"{row_id}:alternative:{index}: tradeoff does not recompute"
                        )
                if (
                    alternative_verification is not None
                    and alternative_verification.to_dict()
                    != alternative.get("lowered_verification_evidence")
                ):
                    failures.append(
                        f"{row_id}:alternative:{index}: lowered evidence "
                        "does not recompute"
                    )
                eligible = bool(
                    alternative_candidate.accounting_status == "emitted"
                    and alternative_candidate.status == "success"
                    and alternative_ideal.status
                    == "verified_ideal_semantics"
                    and alternative_verification is not None
                    and alternative_verification.status.startswith(
                        "verified_lowered_"
                    )
                    and alternative_resources is not None
                    and alternative.get("failure_reason") is None
                )
                resource_tuple = (
                    None
                    if alternative_resources is None
                    else [
                        alternative_resources.t_count,
                        alternative_resources.t_depth,
                        alternative_resources.peak_workspace,
                    ]
                )
                if alternative.get("eligible") != eligible:
                    failures.append(
                        f"{row_id}:alternative:{index}: eligibility mismatch"
                    )
                if alternative.get("resource_tuple") != resource_tuple:
                    failures.append(
                        f"{row_id}:alternative:{index}: resource tuple mismatch"
                    )
                replayed_alternatives.append(
                    {
                        "label": alternative["label"],
                        "eligible": eligible,
                        "resource_tuple": resource_tuple,
                        "operation_signature": _operation_signature(
                            alternative_candidate
                        ),
                    }
                )
            if replayed_alternatives and row.get("selected_from"):
                eligible_alternatives = [
                    value
                    for value in replayed_alternatives
                    if value["eligible"]
                ]
                objective = row.get("objective", "t_count")
                if objective in {"t_count", "t_depth"}:
                    def rank(value):
                        resources = value["resource_tuple"]
                        if objective == "t_depth":
                            return (
                                resources[1],
                                resources[0],
                                resources[2],
                                value["label"],
                            )
                        return (
                            resources[0],
                            resources[1],
                            resources[2],
                            value["label"],
                        )

                    expected_selection = min(
                        eligible_alternatives, key=rank
                    )["label"]
                    if row["selected_from"] != expected_selection:
                        failures.append(
                            f"{row_id}: selected alternative is not the "
                            f"{objective} optimum"
                        )
                selected_artifact = next(
                    (
                        value
                        for value in replayed_alternatives
                        if value["label"] == row["selected_from"]
                    ),
                    None,
                )
                if (
                    selected_artifact is None
                    or selected_artifact["operation_signature"]
                    != row.get("operation_signature")
                ):
                    failures.append(
                        f"{row_id}: selected alternative does not match "
                        "the stored candidate operation stream"
                    )
            replayed_successes += 1
        except Exception as exc:
            failures.append(
                f"{row_id}: artifact replay failed: {exc}"
            )
    return {
        "rows": len(rows),
        "successful_rows": sum(
            row.get("status") == "success" for row in rows
        ),
        "replayed_successful_rows": replayed_successes,
        "failures": failures,
        "status": (
            "verified"
            if rows and not failures
            else "verification_failure"
        ),
        "scope": (
            "schema-v2 target, ideal semantics, deterministic lowering, "
            "independent emitted gates, rotation-arithmetic tradeoffs, "
            "synthesis errors, and resources"
        ),
    }


def _comparison_key(row: dict[str, Any]) -> tuple:
    return tuple(
        row.get(key)
        for key in (
            "target_hash",
            "semantic_profile",
            "preprocessing_version",
            "angle_id",
            "angle_expression",
            "error_budget",
            "error_metric",
            "reuse_count",
            "workspace_budget",
            "model_profile",
            "code_revision",
            "config_hash",
            "manifest_hash",
            "objective",
            "analysis_focus",
            "stratum",
        )
    )


def _paired_rows(
    rows: list[dict[str, Any]],
) -> dict[tuple, dict[str, dict[str, Any]]]:
    revisions = {row.get("code_revision") for row in rows}
    configurations = {row.get("config_hash") for row in rows}
    if len(revisions) > 1 or len(configurations) > 1:
        raise ValueError(
            "result directory mixes code revisions or configurations"
        )
    paired: dict[tuple, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row.get("schema_version") != RESULT_SCHEMA_VERSION:
            raise ValueError(
                "schema-v1 rows cannot enter a schema-v2 comparison"
            )
        key = _comparison_key(row)
        method = row["method"]
        if method in paired[key]:
            raise ValueError(
                f"ambiguous duplicate comparison row for {method}: {key}"
            )
        paired[key][method] = row
    return paired


def _eligible(row: dict[str, Any] | None) -> bool:
    return bool(
        row
        and row.get("status") == "success"
        and row.get("primary_eligible")
        and str(
            row.get("lowered_verification_status", "")
        ).startswith("verified_lowered_")
    )


def _comparison_counts(
    populations: list[dict[str, dict[str, Any]]],
    baseline: str,
) -> dict[str, int]:
    result = {
        "wins": 0,
        "ties": 0,
        "regressions": 0,
        "denominator": 0,
        "zero_denominators": 0,
    }
    for methods in populations:
        candidate = methods.get("dependent_triples_selected")
        reference = methods.get(baseline)
        if not _eligible(candidate) or not _eligible(reference):
            continue
        result["denominator"] += 1
        candidate_t = int(candidate["t_count"])
        reference_t = int(reference["t_count"])
        if reference_t == 0:
            result["zero_denominators"] += 1
        if candidate_t < reference_t:
            result["wins"] += 1
        elif candidate_t == reference_t:
            result["ties"] += 1
        else:
            result["regressions"] += 1
    return result


def render_report(
    rows: list[dict[str, Any]], results_path: Path
) -> str:
    paired = _paired_rows(rows)
    statuses = Counter(row["status"] for row in rows)
    strata = sorted(
        {row.get("stratum", "unclassified") for row in rows}
    )
    lines = [
        "# M2-R Rotation-Arithmetic Tradeoff Evaluation",
        "",
        f"Results: {results_path}",
        "",
        "The primary question in this development pilot is the structural "
        "tradeoff: how many arbitrary rotation syntheses are removed, and "
        "what reversible arithmetic, Clifford work, and clean workspace "
        "replace them. T-count and T-depth are reported as consequences "
        "under one matched lowering configuration, not as the research "
        "objective by themselves.",
        "",
        "Legacy macros and unresolved catalytic or measurement-assisted "
        "estimates are excluded from primary evidence.",
        "",
        "## Status",
        "",
    ]
    lines.extend(
        f"- {status}: {count}"
        for status, count in sorted(statuses.items())
    )
    raw_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for methods in paired.values():
        raw = methods.get("dependent_triples_raw")
        direct = methods.get("independent")
        if _eligible(raw) and _eligible(direct):
            assert raw is not None and direct is not None
            raw_pairs.append((raw, direct))
    raw_pairs.sort(
        key=lambda pair: (
            pair[0].get("stratum", ""),
            pair[0]["case_id"],
        )
    )
    active_pairs = [pair for pair in raw_pairs if pair[0].get("used_rewrite")]
    matched_triples = sum(
        int(raw.get("matched_triples", 0)) for raw, _ in active_pairs
    )
    rotation_delta = sum(
        int(raw["generic_application_rotations"])
        - int(direct["generic_application_rotations"])
        for raw, direct in active_pairs
    )
    toffoli_delta = sum(
        int(raw["logical_toffoli_count"])
        - int(direct["logical_toffoli_count"])
        for raw, direct in active_pairs
    )
    cx_delta = sum(
        int(raw["logical_cx_count"])
        - int(direct["logical_cx_count"])
        for raw, direct in active_pairs
    )
    if matched_triples:
        observed_signature = (
            "The aggregate observed signature per matched triple in this "
            f"pilot is `{rotation_delta / matched_triples:+g}` generic "
            f"rotations, `{toffoli_delta / matched_triples:+g}` logical "
            f"Toffolis, and `{cx_delta / matched_triples:+g}` CNOTs. The "
            "CNOT exchange depends on predicate supports and the parity "
            "network; it is not a universal constant of the identity."
        )
    else:
        observed_signature = "No matched triple was observed in this run."
    lines.extend(
        [
            "",
            "## Raw mechanism tradeoff",
            "",
            "The comparison below uses the raw rule, not the objective-selected "
            "fallback. Deltas are `raw - independent`, so a negative rotation "
            "delta means that the rewrite removed rotation syntheses.",
            "",
            f"The rule fired in {len(active_pairs)} of {len(raw_pairs)} cases "
            f"and matched {matched_triples} disjoint triples. Across the active "
            f"cases it exchanged {-rotation_delta} generic rotations for "
            f"{toffoli_delta} logical Toffolis and {cx_delta} CNOTs. The three "
            "clean workspace qubits are reused across triples within a circuit.",
            "",
            "| Stratum | Case | Triples | Delta generic rotations | "
            "Delta Toffolis | Delta CNOTs | Delta workspace | Delta T | "
            "Delta T-depth |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for raw, direct in raw_pairs:
        lines.append(
            f"| {raw.get('stratum', 'unclassified')} | {raw['case_id']} | "
            f"{raw.get('matched_triples', 0)} | "
            f"{int(raw['generic_application_rotations']) - int(direct['generic_application_rotations']):+d} | "
            f"{int(raw['logical_toffoli_count']) - int(direct['logical_toffoli_count']):+d} | "
            f"{int(raw['logical_cx_count']) - int(direct['logical_cx_count']):+d} | "
            f"{int(raw['peak_workspace']) - int(direct['peak_workspace']):+d} | "
            f"{int(raw['t_count']) - int(direct['t_count']):+d} | "
            f"{int(raw['t_depth']) - int(direct['t_depth']):+d} |"
        )

    lines.extend(
        [
            "",
            observed_signature,
            "",
            "T and T-depth deltas depend on angle, synthesis tolerance, "
            "parallelism, and the number of rotations sharing the total error "
            "budget; they are not the definition of the tradeoff.",
            "",
            "## Absolute construction results",
            "",
            "`Rotations` is shown as generic/exact application requests before "
            "gate decomposition. Toffoli and CNOT counts are logical emitted "
            "operations before Clifford+T lowering.",
            "",
            "| Stratum | Case | Method | Status | Rotations | Toffoli | CNOT | "
            "Workspace | T | T-depth | Error bound | Verification | Primary |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | --- | --- |",
        ]
    )
    for row in sorted(
        rows,
        key=lambda item: (
            item.get("stratum", ""),
            item["case_id"],
            item["method"],
        ),
    ):
        lines.append(
            f"| {row.get('stratum', 'unclassified')} | "
            f"{row['case_id']} | {row['method']} | "
            f"{row['status']} | "
            f"{row.get('generic_application_rotations', 'n/a')}/"
            f"{row.get('exact_application_rotations', 'n/a')} | "
            f"{row.get('logical_toffoli_count', 'n/a')} | "
            f"{row.get('logical_cx_count', 'n/a')} | "
            f"{row.get('peak_workspace') if row.get('peak_workspace') is not None else 'n/a'} | "
            f"{row.get('t_count') if row.get('t_count') is not None else 'n/a'} | "
            f"{row.get('t_depth') if row.get('t_depth') is not None else 'n/a'} | "
            f"{row.get('error_bound') if row.get('error_bound') is not None else 'n/a'} | "
            f"{row.get('lowered_verification_status', 'not_run')} | "
            f"{'yes' if row.get('primary_eligible') else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Secondary deployment-policy comparison",
            "",
            "For completeness, the selected method uses the configured "
            "T-count objective to decide whether to deploy the rewrite or "
            "fall back. These win/tie/regression tables evaluate that policy; "
            "they do not define or discover the structural tradeoff.",
            "",
        ]
    )
    for stratum in strata:
        populations = [
            methods
            for key, methods in paired.items()
            if key[-1] == stratum
        ]
        lines.extend(
            [
                f"### {stratum}",
                "",
                "| Baseline | Wins | Ties | Regressions | "
                "Matched denominator | Zero-T baselines |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for baseline in (*BASIC_BASELINES, *STRONG_BASELINES):
            values = _comparison_counts(populations, baseline)
            lines.append(
                f"| {baseline} | {values['wins']} | "
                f"{values['ties']} | {values['regressions']} | "
                f"{values['denominator']} | "
                f"{values['zero_denominators']} |"
            )
        best = {
            "wins": 0,
            "ties": 0,
            "regressions": 0,
            "denominator": 0,
        }
        for methods in populations:
            candidate = methods.get(
                "dependent_triples_selected"
            )
            references = [
                methods.get(name) for name in STRONG_BASELINES
            ]
            references = [
                value for value in references if _eligible(value)
            ]
            if not _eligible(candidate) or not references:
                continue
            best["denominator"] += 1
            candidate_t = int(candidate["t_count"])
            reference_t = min(
                int(value["t_count"]) for value in references
            )
            if candidate_t < reference_t:
                best["wins"] += 1
            elif candidate_t == reference_t:
                best["ties"] += 1
            else:
                best["regressions"] += 1
        if best["denominator"]:
            lines.extend(
                [
                    "",
                    "Best eligible strong baseline: "
                    f"{best['wins']} wins, {best['ties']} ties, "
                    f"{best['regressions']} regressions on "
                    f"{best['denominator']} matched cases.",
                ]
            )
        else:
            lines.extend(
                ["", "Strong comparison unavailable."]
            )
        lines.append("")

    overlap = 0
    overlap_denominator = 0
    for methods in paired.values():
        raw = methods.get("dependent_triples_raw")
        simplified = methods.get(
            "hwp_dependency_simplified"
        )
        if not _eligible(raw) or not _eligible(simplified):
            continue
        overlap_denominator += 1
        overlap += (
            raw["operation_signature"]
            == simplified["operation_signature"]
        )
    lines.extend(
        [
            "## Structural decision",
            "",
            "The rotation-for-arithmetic exchange above is present and "
            "measurable. Separately, the raw triple and dependency-simplified "
            "HWP artifacts emit "
            f"the same operation stream on {overlap} of "
            f"{overlap_denominator} matched cases.",
            "The current triple construction is therefore subsumed by that "
            "HWP representation wherever the streams match. It remains a "
            "regression and teaching case, not an M3-W novelty witness.",
            "",
            "## Remaining comparison limits",
            "",
            "The emitted ordinary-HWP circuit is a correctness-complete "
            "out-of-place ANF reference. It is not a competitive reproduction "
            "of published in-place or measurement-assisted HWP arithmetic. "
            "Catalytic, measured, and joint-synthesis methods remain "
            "unverified or unavailable and are not ranked.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(
    results_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    path = Path(results_path)
    rows = load_result_rows(path)
    destination = (
        Path(output_path) if output_path else path / "report.md"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_report(rows, path), encoding="utf-8"
    )
    return destination
