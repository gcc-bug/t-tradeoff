from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import yaml

from ..ir import AngleBinding, PhaseProgram, make_program


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("schema_version") not in {1, 2, 3}:
        raise ValueError(f"unsupported config schema in {config_path}")
    config["_path"] = str(config_path.resolve())
    return config


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError(f"unsupported manifest schema in {manifest_path}")
    if not isinstance(manifest.get("cases"), list):
        raise ValueError("manifest cases must be a list")
    manifest["_path"] = str(manifest_path.resolve())
    return manifest


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire_manifest(manifest: dict[str, Any], root: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for case in manifest["cases"]:
        if "source_url" not in case:
            continue
        destination = root / case["local_path"]
        expected = case.get("sha256")
        if not expected:
            raise ValueError(f"remote case {case['id']} has no sha256")
        if destination.exists():
            actual = sha256_file(destination)
            if actual != expected:
                raise ValueError(
                    f"refusing to overwrite checksum-mismatched file {destination}"
                )
            records.append({"case_id": case["id"], "status": "cached", "sha256": actual})
            continue
        request = Request(case["source_url"], headers={"User-Agent": "collective-phase/0.1"})
        with urlopen(request, timeout=60) as response:
            data = response.read()
        actual = sha256_bytes(data)
        if actual != expected:
            raise ValueError(
                f"checksum mismatch for {case['id']}: expected {expected}, got {actual}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        records.append({"case_id": case["id"], "status": "downloaded", "sha256": actual})
    return records


def _parse_maxcut_edgelist(path: Path) -> tuple[int, list[tuple[int, int]]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line and not line.startswith("#")]
    if not lines:
        raise ValueError(f"empty edge-list file: {path}")
    qubit_count = int(lines[0])
    edges: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for line in lines[1:]:
        fields = line.split()
        if len(fields) != 2:
            raise ValueError(f"expected two vertices in {path}: {line!r}")
        u, v = map(int, fields)
        if u == v or not (0 <= u < qubit_count and 0 <= v < qubit_count):
            raise ValueError(f"invalid edge {(u, v)} in {path}")
        edge = (min(u, v), max(u, v))
        if edge in seen:
            raise ValueError(f"duplicate edge {edge} in {path}")
        seen.add(edge)
        edges.append(edge)
    return qubit_count, edges


def _graph_edges(generator: str, parameters: dict[str, Any]) -> tuple[int, list[tuple[int, int]]]:
    if generator == "biclique":
        left, right = int(parameters["a"]), int(parameters["b"])
        return left + right, [(u, left + v) for u in range(left) for v in range(right)]
    n = int(parameters["n"])
    if n < 1:
        raise ValueError("generated graphs require n >= 1")
    if generator in {"path", "weighted_path"}:
        return n, [(u, u + 1) for u in range(n - 1)]
    if generator == "cycle":
        if n < 3:
            raise ValueError("cycles require n >= 3")
        return n, [(u, u + 1) for u in range(n - 1)] + [(0, n - 1)]
    if generator == "star":
        return n, [(0, v) for v in range(1, n)]
    if generator == "triangle":
        if n != 3:
            raise ValueError("the triangle diagnostic requires n=3")
        return 3, [(0, 1), (1, 2), (0, 2)]
    if generator == "clique":
        return n, [(u, v) for u in range(n) for v in range(u + 1, n)]
    raise ValueError(f"unknown graph generator {generator!r}")


def _source_metadata(case: dict[str, Any], source_hash: str) -> dict[str, Any]:
    keys = (
        "source_url",
        "source_revision",
        "dataset_key",
        "license",
        "license_url",
        "seed",
        "complete_workload",
        "stratum",
    )
    result = {key: case[key] for key in keys if key in case}
    result["source_hash"] = source_hash
    result["loader"] = case["loader"]
    result.setdefault("stratum", "unclassified")
    return result


def load_case(case: dict[str, Any], angle: AngleBinding, root: Path) -> PhaseProgram:
    loader = case["loader"]
    coefficients: list[int] | None = None
    edges: list[tuple[int, int]] | None = None
    if loader == "maxcut_edgelist":
        path = root / case["local_path"]
        if not path.exists():
            raise FileNotFoundError(f"run acquire first; missing {path}")
        actual = sha256_file(path)
        if actual != case["sha256"]:
            raise ValueError(f"checksum mismatch for {path}")
        qubit_count, edges = _parse_maxcut_edgelist(path)
        masks = [(1 << u) | (1 << v) for u, v in edges]
        source_hash = actual
    elif loader == "generated_graph":
        qubit_count, edges = _graph_edges(case["generator"], case.get("parameters", {}))
        masks = [(1 << u) | (1 << v) for u, v in edges]
        if case["generator"] == "weighted_path":
            coefficients = list(range(1, len(masks) + 1))
        canonical = json.dumps(case, sort_keys=True, separators=(",", ":")).encode()
        source_hash = sha256_bytes(canonical)
    elif loader == "generated_masks":
        qubit_count = int(case["qubit_count"])
        masks = [int(mask) for mask in case["masks"]]
        coefficients = [int(value) for value in case.get("coefficients", [1] * len(masks))]
        canonical = json.dumps(case, sort_keys=True, separators=(",", ":")).encode()
        source_hash = sha256_bytes(canonical)
    else:
        raise ValueError(f"unknown case loader {loader!r}")
    metadata = _source_metadata(case, source_hash)
    if edges is not None:
        metadata["edges"] = [list(edge) for edge in edges]
        metadata["problem"] = "unweighted_maxcut" if coefficients is None else "weighted_maxcut"
        metadata["phase_convention"] = "P(theta) on x_u XOR x_v"
    return make_program(
        case["id"],
        qubit_count,
        masks,
        angle,
        coefficients=coefficients,
        metadata=metadata,
    )


def load_cases(
    manifest: dict[str, Any], angle: AngleBinding, root: Path
) -> list[PhaseProgram]:
    return [load_case(case, angle, root) for case in manifest["cases"]]
