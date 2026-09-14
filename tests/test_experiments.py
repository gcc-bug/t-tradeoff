import hashlib
import json
from pathlib import Path

import pytest

from collective_phase.experiments import (
    _policy_budget,
    _policy_seconds_budget,
    audit_configuration,
    render_report,
    run_experiments,
    verify_result_rows,
)


def test_static_and_fixed_portfolios_share_total_calls_and_time():
    policies = [
        "static_t", "static_depth", "static_ancilla", "static_balanced",
        "fixed_count_depth", "fixed_depth_count", "adaptive", "frozen",
    ]
    search = {"backend_call_budget": 12, "backend_seconds_budget": 60}
    for members in (policies[:4], policies[4:6]):
        assert sum(_policy_budget(policy, policies, search) for policy in members) == 12
        assert sum(_policy_seconds_budget(policy, policies, search) for policy in members) == 60
    assert _policy_budget("adaptive", policies, search) == 12
    assert _policy_seconds_budget("adaptive", policies, search) == 60


@pytest.fixture
def study(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "data" / "manifests").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='experiment-test'\nversion='0'\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "manifests" / "test.yaml").write_text(
        """schema_version: 1
selection_rule: test-only
cases:
  - id: one
    stratum: synthetic_diagnostic
    loader: generated_masks
    masks: [1]
    qubit_count: 1
    seed: 0
    complete_workload: false
""",
        encoding="utf-8",
    )
    config = {
        "_path": str(tmp_path / "configs" / "test.yaml"),
        "schema_version": 3,
        "manifest": "data/manifests/test.yaml",
        "angles": [{"id": "theta", "value": "pi/4"}],
        "total_error_budgets": [1e-4],
        "workspace_budgets": [0],
        "model_profiles": ["unitary_clifford_t"],
        "policies": ["construction_only", "adaptive"],
        "required_policies": ["construction_only", "adaptive"],
        "objective": "t_count",
        "limits": {"ancilla": 0},
        "hwp_search_cap": 2,
        "seed": 0,
        "search": {
            "backend_call_budget": 1,
            "backend_seconds_budget": 10,
            "actions": ["pyzx:zx_extract"],
        },
        "results_dir": "results/raw/test",
        "diagnosis_path": "reports/test-diagnosis.md",
    }
    rows = run_experiments(config, force=True)
    return tmp_path, config, rows


def test_runner_uses_one_policy_result_format_and_fixed_limits(study):
    root, config, rows = study
    assert len(rows) == 2
    assert {row["policy"] for row in rows} == set(config["policies"])
    assert all(row["schema_version"] == 4 for row in rows)
    assert all(
        row["objective"] == {"mode": "single", "metric": "t_count"}
        for row in rows
    )
    assert all(row["peak_workspace"] == 0 for row in rows)
    verification = verify_result_rows(root / config["results_dir"], root)
    assert verification["status"] == "verified"


def test_case_workspace_budget_caps_search_even_when_global_limit_is_larger(study):
    root, config, _ = study
    variant = dict(config, workspace_budgets=[0, 4], limits={"ancilla": 4})
    rows = run_experiments(variant, force=True)

    assert len(rows) == 4
    for row in rows:
        assert row["limits"]["ancilla"] == row["workspace_budget"]
        assert row["peak_workspace"] <= row["workspace_budget"]
    assert verify_result_rows(root / config["results_dir"], root)["status"] == "verified"


def test_force_run_removes_stale_checkpoints_but_preserves_other_files(study):
    root, config, _ = study
    result_root = root / config["results_dir"]
    (result_root / "stale.json").write_text(
        json.dumps({"schema_version": 2, "row_id": "stale"}), encoding="utf-8"
    )
    (result_root / "circuits" / "stale.json").write_text("{}", encoding="utf-8")
    note = result_root / "notes.txt"
    note.write_text("keep", encoding="utf-8")

    rows = run_experiments(config, force=True)

    assert len(list(result_root.glob("*.json"))) == len(rows)
    assert len(list((result_root / "circuits").glob("*.json"))) == len(rows)
    assert not (result_root / "stale.json").exists()
    assert not (result_root / "circuits" / "stale.json").exists()
    assert note.read_text(encoding="utf-8") == "keep"


def test_stored_consistency_rejects_mutated_artifact(study):
    root, config, rows = study
    row = rows[0]
    artifact_path = root / row["artifact_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["selected"]["resources"][0] += 1
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    result = verify_result_rows(root / config["results_dir"], root)
    assert result["status"] == "verification_failure"
    assert any("checksum mismatch" in value for value in result["failures"])


def test_result_replay_rejects_forged_chain_with_matching_checksum(study):
    root, config, rows = study
    row = next(value for value in rows if value["policy"] == "construction_only")
    artifact_path = root / row["artifact_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    for event in artifact["verified_chain"][0]["events"]:
        if event["kind"] == "t":
            event["kind"] = "tdg"
            break
    else:
        raise AssertionError("expected an exact T gate")
    artifact["lowering"] = artifact["verified_chain"][0]
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    row["artifact_hash"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    (root / config["results_dir"] / f"{row['row_id']}.json").write_text(
        json.dumps(row), encoding="utf-8",
    )
    verification = verify_result_rows(root / config["results_dir"], root)
    assert verification["status"] == "verification_failure"
    assert any("chain replay failed" in value for value in verification["failures"])


def test_result_replay_rejects_forged_pareto_circuit_with_matching_checksum(study):
    root, config, rows = study
    row = next(value for value in rows if value["policy"] == "construction_only")
    artifact_path = root / row["artifact_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    alternative = artifact["pareto_alternatives"][0]
    alternative["verified_chain"][0]["events"][0]["kind"] = "tdg"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    row["artifact_hash"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    (root / config["results_dir"] / f"{row['row_id']}.json").write_text(
        json.dumps(row), encoding="utf-8",
    )

    verification = verify_result_rows(root / config["results_dir"], root)
    assert verification["status"] == "verification_failure"
    assert any("Pareto proof failed" in value for value in verification["failures"])


def test_report_contains_policy_table_trace_and_pareto(study):
    _, _, rows = study
    report = render_report(rows, Path("results/test"))
    assert "## Policy Outcomes" in report
    assert "## Decision Trace" in report
    assert "## Final Pareto Points" in report
    assert "construction_only" in report
    assert "adaptive" in report
    assert "ncf" in report
    assert "trasyn" in report
    assert f"Code revision: `{rows[0]['code_revision']}`" in report


def test_report_rejects_mixed_study_identities(study):
    _, _, rows = study
    changed = dict(rows[0], config_hash="other")
    with pytest.raises(ValueError, match="mixes revisions"):
        render_report([rows[0], changed], Path("results/test"))


def test_report_accepts_distinct_limits_for_distinct_workspace_budgets(study):
    _, _, rows = study
    zero = rows[0]
    four = dict(
        zero, workspace_budget=4,
        limits={"t_count": None, "t_depth": None, "ancilla": 4},
    )
    report = render_report([zero, four], Path("results/test"))
    assert "Hard limits by workspace budget" in report
    assert "| one | theta | 0 |" in report
    assert "| one | theta | 4 |" in report
    with pytest.raises(ValueError, match="mixes hard limits within"):
        render_report([zero, dict(four, workspace_budget=0)], Path("results/test"))


def test_report_distinguishes_static_portfolio_and_fixed_sequences(study):
    _, _, rows = study
    base = rows[0]
    compared = [
        dict(base, policy="static_t", objective_value=2.0),
        dict(base, policy="fixed_count_depth", objective_value=1.0),
        dict(base, policy="adaptive", objective_value=1.0),
    ]

    report = render_report(compared, Path("results/test"))

    assert "static-preference portfolio: 1 wins, 0 ties" in report
    assert "fixed successive-sequence portfolio: 0 wins, 1 ties" in report


def test_audit_reports_optional_backend_blocker(study):
    _, config, _ = study
    audit = audit_configuration(config)
    assert audit["ready"] is True
    assert audit["backends"]["pyzx"]["status"] == "available"
    assert audit["backends"]["feynman"]["status"] in {"available", "unsupported"}


def test_artifact_hash_in_row_matches_bytes(study):
    root, _, rows = study
    for row in rows:
        assert row["artifact_hash"] == hashlib.sha256(
            (root / row["artifact_path"]).read_bytes()
        ).hexdigest()
