import hashlib
import json
from pathlib import Path

import pytest

from collective_phase.experiments import (
    render_report,
    run_experiments,
    verify_result_rows,
)


@pytest.fixture
def stored_run(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "data" / "manifests").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='artifact-test'\nversion='0'\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "manifests" / "test.yaml").write_text(
        """schema_version: 1
selection_rule: test-only
cases:
  - id: mutation_case
    stratum: synthetic_diagnostic
    loader: generated_masks
    masks: [3, 1]
    qubit_count: 2
    seed: 0
    complete_workload: false
""",
        encoding="utf-8",
    )
    config = {
        "_path": str(tmp_path / "configs" / "test.yaml"),
        "schema_version": 2,
        "manifest": "data/manifests/test.yaml",
        "angles": [{"id": "theta", "value": "0.173"}],
        "total_error_budgets": [1e-4],
        "workspace_budgets": [0],
        "model_profiles": ["unitary_clifford_t"],
        "methods": ["independent"],
        "required_methods": ["independent"],
        "objective": "t_count",
        "seed": 0,
        "results_dir": "results/raw/test",
    }
    rows = run_experiments(config)
    assert len(rows) == 1
    assert rows[0]["status"] == "success"
    results = tmp_path / "results" / "raw" / "test"
    assert verify_result_rows(results, tmp_path)["status"] == "verified"
    return tmp_path, results


def _row_path(results):
    return next(
        path
        for path in results.glob("*.json")
        if path.parent == results
    )


def test_replay_rejects_mutated_stored_resource_count(stored_run):
    root, results = stored_run
    path = _row_path(results)
    row = json.loads(path.read_text(encoding="utf-8"))
    row["t_count"] += 1
    path.write_text(json.dumps(row), encoding="utf-8")
    verified = verify_result_rows(results, root)
    assert verified["status"] == "verification_failure"
    assert any("t_count does not recompute" in item for item in verified["failures"])


def test_replay_rejects_mutated_tradeoff_count(stored_run):
    root, results = stored_run
    path = _row_path(results)
    row = json.loads(path.read_text(encoding="utf-8"))
    row["generic_application_rotations"] += 1
    path.write_text(json.dumps(row), encoding="utf-8")
    verified = verify_result_rows(results, root)
    assert verified["status"] == "verification_failure"
    assert any(
        "generic_application_rotations does not recompute" in item
        for item in verified["failures"]
    )


def test_replay_rejects_mutated_event_even_with_updated_hash(stored_run):
    root, results = stored_run
    row_path = _row_path(results)
    row = json.loads(row_path.read_text(encoding="utf-8"))
    artifact_path = root / row["circuit_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    event = next(
        value
        for value in artifact["lowering"]["events"]
        if value["kind"] == "cx"
    )
    event["qubits"].reverse()
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    row["circuit_hash"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    row_path.write_text(json.dumps(row), encoding="utf-8")
    verified = verify_result_rows(results, root)
    assert verified["status"] == "verification_failure"
    assert any("replayed lowering" in item for item in verified["failures"])


def test_replay_rejects_mutated_total_global_phase_token(stored_run):
    root, results = stored_run
    row_path = _row_path(results)
    row = json.loads(row_path.read_text(encoding="utf-8"))
    artifact_path = root / row["circuit_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["lowering"]["total_global_phase"] += 0.25
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    row["circuit_hash"] = hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()
    row_path.write_text(json.dumps(row), encoding="utf-8")
    verified = verify_result_rows(results, root)
    assert verified["status"] == "verification_failure"
    assert any("replayed lowering" in item for item in verified["failures"])


def test_replay_rejects_mutated_total_global_phase_token(stored_run):
    root, results = stored_run
    row_path = _row_path(results)
    row = json.loads(row_path.read_text(encoding="utf-8"))
    artifact_path = root / row["circuit_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["lowering"]["total_global_phase"] += 0.1
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    row["circuit_hash"] = hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()
    row_path.write_text(json.dumps(row), encoding="utf-8")
    verified = verify_result_rows(results, root)
    assert verified["status"] == "verification_failure"
    assert any("replayed lowering" in item for item in verified["failures"])


def test_replay_rejects_nonfinite_row_value(stored_run):
    root, results = stored_run
    path = _row_path(results)
    row = json.loads(path.read_text(encoding="utf-8"))
    row["error_bound"] = float("nan")
    path.write_text(json.dumps(row), encoding="utf-8")
    verified = verify_result_rows(results, root)
    assert verified["status"] == "verification_failure"
    assert any("invalid error_bound" in item for item in verified["failures"])


def test_schema_v1_row_is_excluded_from_primary_evidence(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "old.json").write_text(
        json.dumps({"schema_version": 1, "row_id": "old", "status": "success"}),
        encoding="utf-8",
    )
    verified = verify_result_rows(results, tmp_path)
    assert verified["status"] == "verification_failure"
    assert "unsupported result schema" in verified["failures"][0]


def test_report_leads_with_raw_rotation_arithmetic_tradeoff():
    common = {
        "schema_version": 2,
        "status": "success",
        "primary_eligible": True,
        "lowered_verification_status": "verified_lowered_dense",
        "stratum": "synthetic_diagnostic",
        "case_id": "triple",
        "code_revision": "test-revision",
        "config_hash": "test-config",
        "generic_application_rotations": 3,
        "exact_application_rotations": 0,
        "logical_toffoli_count": 0,
        "logical_cx_count": 6,
        "peak_workspace": 0,
        "t_count": 150,
        "t_depth": 150,
        "error_bound": 1e-5,
        "operation_signature": "direct",
    }
    direct = {**common, "method": "independent"}
    raw = {
        **common,
        "method": "dependent_triples_raw",
        "used_rewrite": True,
        "matched_triples": 1,
        "generic_application_rotations": 1,
        "logical_toffoli_count": 2,
        "logical_cx_count": 12,
        "peak_workspace": 3,
        "t_count": 58,
        "t_depth": 52,
        "operation_signature": "raw",
    }

    report = render_report([direct, raw], Path("results/test"))

    assert report.index("## Raw mechanism tradeoff") < report.index(
        "## Absolute construction results"
    )
    assert "fired in 1 of 1 cases and matched 1 disjoint triples" in report
    assert "| synthetic_diagnostic | triple | 1 | -2 | +2 | +6 | +3 |" in report
