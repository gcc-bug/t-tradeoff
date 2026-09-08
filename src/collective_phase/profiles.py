from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .ir import PhaseProgram


def binary_rank(masks: Iterable[int]) -> int:
    basis: dict[int, int] = {}
    for original in masks:
        value = original
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = value
                break
            value ^= basis[pivot]
    return len(basis)


def fundamental_dependencies(masks: list[int]) -> list[list[int]]:
    """Return deterministic GF(2) dependency witnesses by input index."""
    basis: dict[int, tuple[int, int]] = {}
    dependencies: list[list[int]] = []
    for index, original in enumerate(masks):
        value = original
        combination = 1 << index
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (value, combination)
                break
            row, row_combination = basis[pivot]
            value ^= row
            combination ^= row_combination
        if value == 0:
            dependencies.append(
                [position for position in range(len(masks)) if (combination >> position) & 1]
            )
    return dependencies


def dependent_triples(masks: Iterable[int]) -> list[tuple[int, int, int]]:
    unique = sorted(set(mask for mask in masks if mask))
    available = set(unique)
    triples: set[tuple[int, int, int]] = set()
    for position, first in enumerate(unique):
        for second in unique[position + 1 :]:
            third = first ^ second
            if third in available and third != first and third != second:
                triples.add(tuple(sorted((first, second, third))))
    return sorted(triples)


@dataclass(frozen=True)
class StructuralProfile:
    case_id: str
    variables: int
    term_count: int
    unique_parities: int
    duplicate_multiplicities: dict[str, int]
    exact_angle_classes: dict[str, int]
    binary_rank: int
    dependency_witnesses: list[list[int]]
    dependent_triples: list[list[int]]
    support_histogram: dict[str, int]
    graph: dict[str, Any] | None
    coverage_fraction: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _graph_profile(program: PhaseProgram) -> dict[str, Any] | None:
    edges = program.metadata.get("edges")
    if edges is None:
        return None
    adjacency: dict[int, set[int]] = {node: set() for node in range(program.qubit_count)}
    for u, v in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)
    visited: set[int] = set()
    component_sizes: list[int] = []
    for start in adjacency:
        if start in visited:
            continue
        queue = deque([start])
        visited.add(start)
        size = 0
        while queue:
            node = queue.popleft()
            size += 1
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        component_sizes.append(size)
    neighborhoods = Counter(tuple(sorted(values)) for values in adjacency.values())
    triangle_count = sum(
        1
        for u in adjacency
        for v in adjacency[u]
        if u < v
        for w in adjacency[u] & adjacency[v]
        if v < w
    )
    return {
        "edge_count": len(edges),
        "degree_sequence": sorted((len(values) for values in adjacency.values()), reverse=True),
        "component_sizes": sorted(component_sizes, reverse=True),
        "repeated_neighborhood_multiplicities": sorted(
            (count for count in neighborhoods.values() if count > 1), reverse=True
        ),
        "triangle_count": triangle_count,
    }


def profile(program: PhaseProgram) -> StructuralProfile:
    masks = [term.mask for term in program.terms]
    multiplicities = Counter(masks)
    angle_counts = Counter(term.angle_id for term in program.terms)
    triples = dependent_triples(masks)
    covered = {mask for triple in triples for mask in triple}
    support_counts = Counter(mask.bit_count() for mask in masks)
    return StructuralProfile(
        case_id=program.id,
        variables=program.qubit_count,
        term_count=len(masks),
        unique_parities=len(multiplicities),
        duplicate_multiplicities={str(mask): count for mask, count in sorted(multiplicities.items())},
        exact_angle_classes=dict(sorted(angle_counts.items())),
        binary_rank=binary_rank(masks),
        dependency_witnesses=fundamental_dependencies(masks),
        dependent_triples=[list(triple) for triple in triples],
        support_histogram={str(size): count for size, count in sorted(support_counts.items())},
        graph=_graph_profile(program),
        coverage_fraction=(
            sum(1 for mask in masks if mask in covered) / len(masks) if masks else 0.0
        ),
    )

