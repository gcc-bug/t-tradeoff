from pathlib import Path

import pytest

from collective_phase.inputs.manifest import load_case, load_config
from collective_phase.ir import AngleBinding, make_program
from collective_phase.profiles import binary_rank, dependent_triples, profile


def test_config_loader_accepts_current_schema(tmp_path: Path):
    config_path = tmp_path / "study.yaml"
    config_path.write_text("schema_version: 3\nrun_id: test\n", encoding="utf-8")

    config = load_config(config_path)

    assert config["schema_version"] == 3
    assert config["_path"] == str(config_path.resolve())


def test_config_loader_rejects_unknown_schema(tmp_path: Path):
    config_path = tmp_path / "study.yaml"
    config_path.write_text("schema_version: 4\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported config schema"):
        load_config(config_path)


def test_maxcut_loader_uses_xor_parities_and_declared_bit_order(tmp_path: Path):
    source = tmp_path / "graph.txt"
    source.write_text("3\n0 1\n1 2\n", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    case = {
        "id": "graph",
        "loader": "maxcut_edgelist",
        "local_path": "graph.txt",
        "sha256": digest,
        "complete_workload": True,
    }
    program = load_case(case, AngleBinding("theta", "0.3"), tmp_path)
    assert [term.mask for term in program.terms] == [0b011, 0b110]
    assert program.integer_values(0b001)["theta"] == 1


def test_loader_rejects_duplicate_undirected_edges(tmp_path: Path):
    source = tmp_path / "graph.txt"
    source.write_text("2\n0 1\n1 0\n", encoding="utf-8")
    import hashlib

    case = {
        "id": "bad",
        "loader": "maxcut_edgelist",
        "local_path": "graph.txt",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    with pytest.raises(ValueError, match="duplicate edge"):
        load_case(case, AngleBinding("theta", "0.3"), tmp_path)


def test_rank_dependencies_and_dependent_triple_profile():
    masks = [1, 2, 3]
    assert binary_rank(masks) == 2
    assert dependent_triples(masks) == [(1, 2, 3)]
    result = profile(make_program("triple", 2, masks, AngleBinding("theta", "0.4")))
    assert result.binary_rank == 2
    assert result.dependency_witnesses == [[0, 1, 2]]
    assert result.coverage_fraction == 1.0


def test_graph_profile_counts_triangles_once():
    program = make_program(
        "triangle",
        3,
        [3, 6, 5],
        AngleBinding("theta", "0.4"),
        metadata={"edges": [[0, 1], [1, 2], [0, 2]], "source_hash": "x"},
    )
    assert profile(program).graph["triangle_count"] == 1
