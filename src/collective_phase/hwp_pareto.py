"""Finite-library HWP synthesis with exact Pareto labels and complete-block waves.

Exactness is restricted to this library, fixed normalized-term precision policy,
and barrier-separated waves. It is not an optimality claim after gate rewriting.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from itertools import combinations, product
import math
import time

from .baselines.common import CompilationConstraints, batch_sizes
from .baselines.hwp import compile_hwp_adder_unitary
from .baselines.independent import compile_independent
from .circuit import Candidate, data_support
from .ir import ParityTerm, PhaseBlock, PhaseProgram
from .lowering import LoweredCircuit, RotationSynthesizer, lower_candidate
from .lowering.lower import lower_candidate_with_rotations
from .preprocessing import NormalizedTerm, preprocess
from .resources import estimate_resources
from .selection import dominates_resources
from .verification import verify_lowered_circuit

Resources = tuple[int, int, int]


@dataclass(frozen=True)
class BlockOption:
    id: int
    terms: int
    group: int
    boundary: int
    footprint: int
    data_wires: tuple[int, ...]
    layout: str
    resources: Resources
    lowered: LoweredCircuit = field(compare=False, repr=False)
    allowance: float

    def summary(self) -> dict:
        return {"id": self.id, "terms": self.terms, "group": self.group,
                "boundary": self.boundary, "footprint": self.footprint,
                "data_wires": self.data_wires, "layout": self.layout,
                "resources": self.resources, "allowance": self.allowance,
                "error_bound": self.lowered.error_bound}


@dataclass
class Library:
    program: PhaseProgram
    terms: tuple[NormalizedTerm, ...]
    groups: tuple[tuple[int, ...], ...]
    options: tuple[BlockOption, ...]
    total_error: float
    max_batch: int
    stats: dict

    @property
    def full_mask(self) -> int:
        return (1 << len(self.terms)) - 1


@dataclass(frozen=True)
class Plan:
    resources: Resources
    waves: tuple[tuple[int, ...], ...] = ()

    def to_dict(self) -> dict:
        return {"resources": self.resources, "waves": self.waves}


def pareto(plans) -> list[Plan]:
    """One deterministic reconstruction per distinct nondominated tuple."""
    best: dict[Resources, Plan] = {}
    for plan in plans:
        old = best.get(plan.resources)
        if old is None or plan.waves < old.waves:
            best[plan.resources] = plan
    front: list[Plan] = []
    for plan in sorted(best.values(), key=lambda p: (p.resources, p.waves)):
        if not any(dominates_resources(other.resources, plan.resources) for other in front):
            front.append(plan)
    return front


def build_library(program: PhaseProgram, total_error: float,
                  synthesizer: RotationSynthesizer, *, max_batch: int = 10,
                  max_terms: int = 10) -> Library:
    started = time.perf_counter()
    if not math.isfinite(total_error) or not 0 < total_error < 1:
        raise ValueError("total_error must lie in (0, 1)")
    if max_batch < 1 or max_terms < 1:
        raise ValueError("positive size limits required")
    normalized = preprocess(program)
    if len(normalized.terms) > max_terms or program.qubit_count > 10:
        raise ValueError("instance exceeds the declared exact-search/verification cap")
    indices = {term.id: i for i, term in enumerate(normalized.terms)}
    boundaries = {block.id: i for i, block in enumerate(program.blocks)}
    if len(boundaries) != len(program.blocks):
        raise ValueError("block IDs must be unique")
    groups = tuple(tuple(indices[t.id] for t in g.terms) for g in normalized.groups)
    templates: dict[tuple, LoweredCircuit] = {}
    options: list[BlockOption] = []
    hits = 0
    for group_id, group in enumerate(normalized.groups):
        for size in range(1, min(max_batch, len(group.terms)) + 1):
            for subset in combinations(group.terms, size):
                footprint = 0
                for term in subset:
                    footprint |= term.mask
                wires = tuple(data_support(footprint))
                local_masks = tuple(sum(((t.mask >> q) & 1) << i for i, q in enumerate(wires))
                                    for t in subset)
                native = (group.coefficient == 1 and
                          all(mask.bit_count() == 1 for mask in local_masks))
                layouts = ("direct",) if size == 1 else (
                    ("in_place_inputs", "copied_parities") if native else ("copied_parities",))
                allowance = total_error * size / max(1, len(normalized.terms))
                for layout in layouts:
                    # Compact-wire templates retain predicate structure; no unproved
                    # permutation equivalence is used for overlapping parities.
                    key = (local_masks, group.angle_id, group.coefficient, layout, allowance)
                    if key not in templates:
                        local = PhaseProgram(
                            "hwp-template", len(wires), program.angles,
                            (PhaseBlock("block", tuple(ParityTerm(f"p{i}", mask, group.angle_id,
                                coefficient=group.coefficient) for i, mask in enumerate(local_masks))),))
                        constraints = CompilationConstraints(None, "unitary_clifford_t",
                                                             hwp_search_cap=max_batch)
                        candidate = (compile_independent(local, constraints) if layout == "direct"
                                     else compile_hwp_adder_unitary(local, constraints,
                                                                  batch_limit=size, layout=layout))
                        lowered = lower_candidate(candidate, allowance, synthesizer)
                        proof = verify_lowered_circuit(lowered, allowance, memory_cap_bytes=1)
                        if not proof.status.startswith("verified_lowered_"):
                            raise ValueError(f"invalid library entry: {proof.message}")
                        templates[key] = lowered
                    else:
                        hits += 1
                    lowered = templates[key]
                    r = estimate_resources(lowered)
                    options.append(BlockOption(
                        len(options), sum(1 << indices[t.id] for t in subset), group_id,
                        boundaries[group.block_id], footprint, wires, layout,
                        (r.t_count, r.t_depth, r.peak_workspace), lowered, allowance))
    return Library(program, normalized.terms, groups, tuple(options), total_error, max_batch,
                   {"seconds": time.perf_counter() - started, "options": len(options),
                    "templates": len(templates), "template_hits": hits,
                    "normalized_terms": len(normalized.terms),
                    "subset_coverage": "all nonempty compatible subsets up to max_batch"})


class _Deadline(Exception):
    pass


@dataclass
class FrontierResult:
    status: str
    plans: list[Plan]
    complete: bool
    stats: dict

    def solve(self, ancilla_max: int, depth_max: int) -> dict:
        _validate_limits(ancilla_max, depth_max)
        if (ancilla_max > self.stats["ancilla_max"] or
                (self.stats["depth_max"] is not None and depth_max > self.stats["depth_max"])):
            raise ValueError("query exceeds the solved resource range")
        eligible = [p for p in self.plans if p.resources[1] <= depth_max
                    and p.resources[2] <= ancilla_max]
        best = min(eligible, key=lambda p: p.resources, default=None)
        return {"status": ("OPTIMAL" if self.complete else "FEASIBLE") if best else
                ("INFEASIBLE" if self.complete else "TIMEOUT"),
                "plan": None if best is None else best.to_dict(),
                "guarantee": "finite library, fixed precision, wave model"}


def _validate_limits(ancilla_max: int, depth_max: int | None) -> None:
    if type(ancilla_max) is not int or ancilla_max < 0:
        raise ValueError("ancilla cap must be a nonnegative integer")
    if depth_max is not None and (type(depth_max) is not int or depth_max < 0):
        raise ValueError("depth cap must be a nonnegative integer")


def frontier(library: Library, ancilla_max: int, depth_max: int | None = None, *,
             timeout_seconds: float = 60, option_ids: frozenset[int] | None = None) -> FrontierResult:
    """Exact subset DP; a timeout returns only complete feasible incumbents.

    Canonical waves contain the first remaining term. Reordering is permitted
    only within one original diagonal block, never across block boundaries.
    """
    _validate_limits(ancilla_max, depth_max)
    if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
        raise ValueError("timeout must be finite and nonnegative")
    started = time.perf_counter()
    deadline = started + timeout_seconds
    stats = {"states": 0, "waves": 0, "labels_considered": 0, "peak_labels_per_state": 0,
             "ancilla_max": ancilla_max, "depth_max": depth_max}
    options = [o for o in library.options if o.resources[2] <= ancilla_max and
               (option_ids is None or o.id in option_ids)]
    by_term = {i: [o for o in options if o.terms & (1 << i)] for i in range(len(library.terms))}
    incumbents: list[Plan] = []
    # Cheap serial direct incumbent, with the exact same library and error policy.
    singles = [next((o for o in by_term[i] if o.terms == 1 << i), None)
               for i in range(len(library.terms))]
    if all(o is not None for o in singles):
        p = Plan((sum(o.resources[0] for o in singles), sum(o.resources[1] for o in singles), 0),
                 tuple((o.id,) for o in singles))
        if depth_max is None or p.resources[1] <= depth_max:
            incumbents.append(p)

    def check_time():
        if time.perf_counter() >= deadline:
            raise _Deadline

    def waves(remaining: int):
        anchor = (remaining & -remaining).bit_length() - 1
        boundary = min(o.boundary for o in by_term[anchor]) if by_term[anchor] else -1
        eligible = [o for o in options if o.terms & remaining == o.terms and o.boundary == boundary]
        # Distinct covers may have different continuations. Only prune within cover.
        by_cover: dict[int, list[Plan]] = {}
        def extend(chosen, cover, footprint, resources, first):
            check_time()
            stats["waves"] += 1
            by_cover.setdefault(cover, []).append(Plan(resources, (tuple(sorted(chosen)),)))
            for index in range(first, len(eligible)):
                opt = eligible[index]
                if opt.terms & cover or opt.footprint & footprint:
                    continue
                t, d, a = opt.resources
                if resources[2] + a > ancilla_max:
                    continue
                extend((*chosen, opt.id), cover | opt.terms, footprint | opt.footprint,
                       (resources[0] + t, max(resources[1], d), resources[2] + a), index + 1)
        for opt in by_term[anchor]:
            if opt.terms & remaining == opt.terms:
                extend((opt.id,), opt.terms, opt.footprint, opt.resources, 0)
        for cover, plans in by_cover.items():
            for plan in pareto(plans):
                yield cover, plan

    @lru_cache(None)
    def visit(remaining: int) -> tuple[Plan, ...]:
        check_time()
        stats["states"] += 1
        if remaining == 0:
            return (Plan((0, 0, 0)),)
        labels: list[Plan] = []
        for cover, wave in waves(remaining):
            for tail in visit(remaining ^ cover):
                stats["labels_considered"] += 1
                t, d, a = wave.resources
                resources = (t + tail.resources[0], d + tail.resources[1], max(a, tail.resources[2]))
                if depth_max is not None and resources[1] > depth_max:
                    continue
                plan = Plan(resources, wave.waves + tail.waves)
                labels.append(plan)
                if remaining == library.full_mask:
                    incumbents.append(plan)
            if len(labels) > 256:
                labels = pareto(labels)
        result = tuple(pareto(labels))
        stats["peak_labels_per_state"] = max(stats["peak_labels_per_state"], len(result))
        return result

    try:
        plans = list(visit(library.full_mask))
        complete = True
    except _Deadline:
        plans, complete = pareto(incumbents), False
    stats.update(seconds=time.perf_counter() - started, cache_hits=visit.cache_info().hits)
    return FrontierResult(("OPTIMAL" if plans else "INFEASIBLE") if complete else
                          ("FEASIBLE" if plans else "TIMEOUT"), plans, complete, stats)


def solve(library: Library, ancilla_max: int, depth_max: int, **kwargs) -> dict:
    return frontier(library, ancilla_max, depth_max, **kwargs).solve(ancilla_max, depth_max)


def emit(library: Library, plan: Plan, *, memory_cap_bytes: int = 1) -> tuple[LoweredCircuit, dict]:
    """Reuse clean scratch between waves; rebuild gates from persisted rotations."""
    n = library.program.qubit_count
    operations, rotations, error_blocks, wave_trace = [], [], [], []
    covered = 0
    total_t = total_d = peak_a = 0
    last_boundary = -1
    for wave in plan.waves:
        if not wave:
            raise ValueError("empty wave")
        footprint = scratch = wave_t = wave_d = 0
        bounds = {library.options[i].boundary for i in wave}
        if len(bounds) != 1 or min(bounds) < last_boundary:
            raise ValueError("wave crosses or reverses an original block boundary")
        last_boundary = min(bounds)
        blocks = []
        for i in wave:
            opt = library.options[i]
            if covered & opt.terms or footprint & opt.footprint:
                raise ValueError("overlapping coverage or wave data footprints")
            covered |= opt.terms
            footprint |= opt.footprint
            local = opt.lowered.candidate
            mapping = {q: wire for q, wire in enumerate(opt.data_wires)}
            mapping.update({local.program.qubit_count + q: n + scratch + q
                            for q in range(local.workspace_qubits)})
            start = len(operations)
            operations.extend(replace(op, qubits=tuple(mapping[q] for q in op.qubits))
                              for op in local.operations)
            rotations.extend(opt.lowered.application_rotations)
            error_blocks.append({"operations": [start, len(operations)],
                "term_ids": [t.id for j, t in enumerate(library.terms) if opt.terms & (1 << j)]})
            blocks.append({"option": i, "scratch": list(range(n + scratch, n + scratch + local.workspace_qubits)),
                           "operations": [start, len(operations)]})
            scratch += opt.resources[2]
            wave_t += opt.resources[0]
            wave_d = max(wave_d, opt.resources[1])
        total_t += wave_t
        total_d += wave_d
        peak_a = max(peak_a, scratch)
        wave_trace.append({"blocks": blocks, "resources": [wave_t, wave_d, scratch],
                           "barrier_after": True})
    if covered != library.full_mask or (total_t, total_d, peak_a) != plan.resources:
        raise ValueError("incomplete coverage or inconsistent plan resources")
    candidate = Candidate("hwp_pareto", "0.1", library.program, "success", operations,
                          peak_a, preprocess(library.program).global_phase,
                          parameters={"term_error_blocks": error_blocks,
                                      "precision_policy": "normalized_term_blocks_v1",
                                      "wave_schedule": wave_trace},
                          implementation_family="unitary_hwp_wave_plan", variant="pareto",
                          preprocessing_version="canonical-v2")
    lowered = lower_candidate_with_rotations(candidate, library.total_error, rotations, [])
    proof = verify_lowered_circuit(lowered, library.total_error, memory_cap_bytes=memory_cap_bytes)
    if not proof.status.startswith("verified_lowered_"):
        raise ValueError(f"composed circuit failed verification: {proof.message}")
    r = estimate_resources(lowered)
    if r.t_count != total_t or r.t_depth > total_d or r.peak_workspace != peak_a:
        raise ValueError("emitted resources violate wave upper bounds")
    return lowered, proof.to_dict()


def _partitions(indices: tuple[int, ...], sizes: tuple[int, ...]):
    """All subset assignments with a prescribed multiset of block sizes."""
    if not indices:
        yield ()
        return
    anchor, *rest = indices
    for size in sorted(set(sizes)):
        remaining_sizes = list(sizes)
        remaining_sizes.remove(size)
        for others in combinations(rest, size - 1):
            group = (anchor, *others)
            left = tuple(i for i in rest if i not in others)
            for tail in _partitions(left, tuple(remaining_sizes)):
                yield (sum(1 << i for i in group), *tail)


def baseline_frontiers(library: Library, ancilla_max: int, *, timeout_seconds: float = 120) -> dict:
    """Best uniform/per-group caps with balanced AND full-plus-remainder batches.

    Enumerates membership assignments and exact legal wave schedules. Each group
    chooses one HWP layout, with direct fallback allowed per batch. This is
    stronger than fixed contiguous batching or forcing unprofitable remainders.
    """
    started = time.perf_counter()
    options = {(o.terms, o.layout): o.id for o in library.options}
    partition_cache: dict[tuple[int, ...], list[Plan]] = {}
    output = {"direct": [], "uniform": [], "per_group": []}
    complete = True
    group_choices = []
    for group in library.groups:
        choices = set()
        for cap in range(1, library.max_batch + 1):
            n = len(group)
            shapes = {tuple(sorted(batch_sizes(n, cap, "balanced"))),
                      tuple(sorted([cap] * (n // cap) + ([n % cap] if n % cap else [])))}
            for shape in shapes:
                for partition in _partitions(group, shape):
                    for layout in ("auto", "in_place_inputs", "copied_parities"):
                        keys = []
                        for mask in partition:
                            kind = "direct" if mask.bit_count() == 1 else layout
                            if kind == "auto":
                                kind = ("in_place_inputs" if (mask, "in_place_inputs") in options
                                        else "copied_parities")
                            keys.append((mask, kind))
                        # A fair uniform baseline may leave an unprofitable
                        # batch as direct rotations; it must not pay gratuitous
                        # HWP arithmetic merely because a cap was selected.
                        alternatives = []
                        for mask, kind in keys:
                            direct = tuple(options[1 << i, "direct"] for i in group if mask & (1 << i))
                            variants = {direct}
                            if (mask, kind) in options:
                                variants.add((options[mask, kind],))
                            alternatives.append(sorted(variants))
                        for selected in product(*alternatives):
                            choices.add((cap, tuple(sorted(i for batch in selected for i in batch))))
        group_choices.append(sorted(choices))
    try:
        for combination in product(*group_choices):
            ids = tuple(sorted(i for _, group_ids in combination for i in group_ids))
            if ids not in partition_cache:
                remaining = timeout_seconds - (time.perf_counter() - started)
                if remaining <= 0:
                    raise _Deadline
                result = frontier(library, ancilla_max, timeout_seconds=remaining,
                                  option_ids=frozenset(ids))
                if not result.complete:
                    raise _Deadline
                partition_cache[ids] = result.plans
            plans = partition_cache[ids]
            output["per_group"].extend(plans)
            if len({cap for cap, _ in combination}) <= 1:
                output["uniform"].extend(plans)
            if all(library.options[i].layout == "direct" for i in ids):
                output["direct"].extend(plans)
    except _Deadline:
        complete = False
    return {"frontiers": {name: pareto(plans) for name, plans in output.items()},
            "complete": complete, "partitions": len(partition_cache),
            "seconds": time.perf_counter() - started}
