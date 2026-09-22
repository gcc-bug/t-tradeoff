"""Exact rational cost-directed search over the existing complete-wave library.

Certificates are local, source-backed records, not untrusted imported assertions.
A Model is a frozen study context: its library must not be mutated after creation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
import heapq
import json
import math
from pathlib import Path
import time

from .hwp_pareto import Library, Plan, _Deadline, _validate_limits, canonical_waves, emit
from .resources import estimate_resources


def rational(value) -> Fraction:
    """Decimal strings (including decimal config numbers) are parsed exactly."""
    return value if isinstance(value, Fraction) else Fraction(str(value))


def weights(values) -> tuple[Fraction, ...]:
    result = tuple(map(rational, values))
    if len(result) != 3 or min(result) < 0 or not any(result):
        raise ValueError('three nonnegative weights, not all zero, required')
    return result


def cost(resources, coefficients):
    return sum((w*r for w, r in zip(coefficients, resources)), Fraction(0))


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Model:
    library: Library = field(repr=False, compare=False)
    fingerprint: str = field(init=False)

    def __post_init__(self):
        root = Path(__file__).parent
        templates = {id(o.lowered): o.lowered for o in self.library.options}
        evidence = {'input': self.library.program.to_dict(), 'batch_cap': self.library.max_batch,
                    'total_error': self.library.total_error, 'precision': 'normalized_term_blocks_v1',
                    'synthesis_seed': self.library.stats['synthesis_seed'],
                    'wave_rules': 'canonical_complete_disjoint_data_original_boundaries_v1',
                    'ancillas': 'clean_restored_at_block_boundaries; sum_within_wave; peak_across_waves',
                    'source': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(root.rglob('*.py'))},
                    'options': [o.summary() for o in self.library.options],
                    'templates': [{'candidate': t.candidate.to_dict(), 'lowering': t.to_dict()}
                                  for t in templates.values()]}
        object.__setattr__(self, 'fingerprint', _digest(evidence))

    def query_fingerprint(self, ancilla_max, depth_max):
        _validate_limits(ancilla_max, depth_max)
        return _digest([self.fingerprint, ancilla_max, depth_max])


def completion_bounds(library, remaining, options=None):
    """Fractional per-term T charges; individual minimum block depth/scratch.

    Options form a superset of legal completion options. Omitting wave conflicts
    relaxes the problem. None means a remaining term has no covering option.
    """
    if not remaining:
        return (Fraction(0), 0, 0)
    eligible = [o for o in (library.options if options is None else options)
                if o.terms & remaining == o.terms]
    t, d, a = Fraction(0), 0, 0
    for i in range(len(library.terms)):
        if remaining & (1 << i):
            cover = [o for o in eligible if o.terms & (1 << i)]
            if not cover:
                return None
            t += min(Fraction(o.resources[0], o.terms.bit_count()) for o in cover)
            d = max(d, min(o.resources[1] for o in cover))
            a = max(a, min(o.resources[2] for o in cover))
    return t, d, a


def coupled_completion_bounds(library, remaining, options, ancilla_max, check_time=lambda: None):
    """Fractional resource loads, with complete-wave coupling relaxed.

    Each term receives the minimum share of a covering block's resource load.
    Disjoint coverage therefore charges no selected block more than its load.
    Blocks using one data wire execute in different waves. Also sum(a*d) <= A*D
    within each boundary. Boundaries cannot share waves, so their depth bounds
    add. These are lower bounds, not feasible schedules or local scalar choices.
    """
    eligible = [o for o in options if o.terms & remaining == o.terms]
    base = completion_bounds(library, remaining, eligible)
    if base is None or not remaining:
        return base
    boundaries = {}
    for o in eligible:
        boundaries.setdefault(o.boundary, []).append(o)
    depth = Fraction(0)
    for group in boundaries.values():
        check_time()
        mask = footprint = 0
        for o in group:
            mask |= o.terms
            footprint |= o.footprint
        wires = [q for q in range(footprint.bit_length()) if footprint & (1 << q)]
        loads = {q: Fraction(0) for q in wires}
        volume, individual = Fraction(0), 0
        for i in range(len(library.terms)):
            if not mask & (1 << i):
                continue
            cover = [o for o in group if o.terms & (1 << i)]
            individual = max(individual, min(o.resources[1] for o in cover))
            volume += min(Fraction(o.resources[1]*o.resources[2], o.terms.bit_count()) for o in cover)
            for q in wires:
                loads[q] += min(Fraction(o.resources[1], o.terms.bit_count())
                                if o.footprint & (1 << q) else Fraction(0) for o in cover)
        depth += max(individual, max(loads.values(), default=0),
                     volume / ancilla_max if ancilla_max else 0)
    return base[0], max(base[1], depth), base[2]


@dataclass(frozen=True)
class OpenWave:
    """An unfinished wave family; cursor excludes already generated siblings."""
    chosen: tuple[int, ...] = ()
    cover: int = 0
    footprint: int = 0
    cursor: int = 0
    close_pending: bool = False


@dataclass(frozen=True)
class SearchResult:
    status: str
    reason: str
    plan: Plan | None
    lower: Fraction | None
    upper: Fraction | None
    coefficients: tuple[Fraction, ...]
    fingerprint: str
    stats: dict = field(compare=False)

    @property
    def absolute_gap(self):
        return None if self.upper is None or self.lower is None else self.upper-self.lower

    @property
    def relative_gap(self):
        return self.absolute_gap/self.lower if self.lower is not None and self.lower > 0 and self.upper is not None else None


@dataclass(frozen=True)
class CertifiedInequality:
    coefficients: tuple[Fraction, ...]
    bound: Fraction
    fingerprint: str
    source: SearchResult = field(repr=False, compare=False)

    @classmethod
    def from_result(cls, result):
        if not isinstance(result.lower, Fraction) or result.status not in {'OPTIMAL', 'FEASIBLE', 'TIMEOUT'}:
            raise ValueError('no certified lower bound in source')
        return cls(result.coefficients, result.lower, result.fingerprint, result)

    def validate(self, fingerprint):
        if self.fingerprint != fingerprint or self.source.fingerprint != fingerprint:
            raise ValueError('certificate model/feasibility fingerprint mismatch')
        if (not isinstance(self.bound, Fraction) or not isinstance(self.source.lower, Fraction) or
                any(not isinstance(v, Fraction) for v in self.coefficients) or
                self.coefficients != weights(self.source.coefficients) or
                self.bound != self.source.lower or self.bound < 0 or
                self.source.status not in {'OPTIMAL', 'FEASIBLE', 'TIMEOUT'} or
                (self.source.upper is not None and self.bound > self.source.upper)):
            raise ValueError('invalid certificate or inconsistent certification source')


def transferred_bound(certificates, target, fingerprint):
    """Best single-certificate scaling, checked exactly component by component."""
    target = weights(target)
    bound = Fraction(0)
    for cert in certificates:
        cert.validate(fingerprint)
        scale = min(w/v for w,v in zip(target, cert.coefficients) if v > 0)
        if scale < 0 or any(scale*v > w for v,w in zip(cert.coefficients, target)):
            raise ValueError('invalid transfer multipliers')
        bound = max(bound, scale*cert.bound)
    return bound


def search(model: Model, coefficients, ancilla_max, depth_max=None, *, seeds=(),
           structural=True, certificates=(), timeout_seconds=60, tolerance='0',
           clock=time.perf_counter) -> SearchResult:
    """One best-first engine, with deterministic ties and safe prefix dominance.

    The active parent remains pending until *all* its successors are generated.
    Lower bounds include this pending subtree when a deadline interrupts expansion.
    Seeds and every improved incumbent are emitted and verified before use as U.
    Verification errors raise ValueError; they are never reported as infeasibility.
    """
    started = clock()
    if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
        raise ValueError('timeout must be finite and nonnegative')
    eta = rational(tolerance)
    if eta < 0:
        raise ValueError('negative tolerance')
    w = weights(coefficients)
    fp = model.query_fingerprint(ancilla_max, depth_max)
    library = model.library
    archive = transferred_bound(certificates, w, fp)
    stats = {'states': 0, 'waves': 0, 'dominated': 0, 'bound_pruned': 0,
             'verification_seconds': 0., 'first_improvement_seconds': None,
             'gap_5_percent_seconds': None, 'gap_1_percent_seconds': None,
             'pending_expansion_at_timeout': False, 'archive_lower': str(archive)}
    incumbent, upper = None, None

    def feasible(r):
        return r[2] <= ancilla_max and (depth_max is None or r[1] <= depth_max)

    def verify(plan):
        t = clock()
        lowered, proof = emit(library, plan)
        stats['incumbent_verification'] = proof
        stats['incumbent_emitted'] = estimate_resources(lowered).to_dict()
        stats['verification_seconds'] += clock()-t

    seeds = tuple(seeds)
    if any(len(p.resources) != 3 or any(type(r) is not int or r < 0 for r in p.resources) for p in seeds):
        raise ValueError('seed resources must be exact nonnegative integers')
    eligible_seeds = [p for p in seeds if feasible(p.resources)]
    if eligible_seeds:
        incumbent = min(eligible_seeds, key=lambda p: (cost(p.resources,w), p.resources, p.waves))
        verify(incumbent)
        upper = cost(incumbent.resources,w)
    stats['seed_upper'] = None if upper is None else str(upper)
    options = [o for o in library.options if o.resources[2] <= ancilla_max]
    by_term = {i: [o for o in options if o.terms & (1 << i)] for i in range(len(library.terms))}

    @lru_cache(None)
    def bounds(remaining):
        return completion_bounds(library, remaining, options) if structural else (Fraction(0), 0, 0)

    def node_bound(remaining, resources):
        tail = bounds(remaining)
        if tail is None:
            return None
        r = (resources[0]+tail[0], resources[1]+tail[1], max(resources[2],tail[2]))
        return max(cost(r,w), archive) if feasible(r) else None

    queue, serial = [], 0
    root = node_bound(library.full_mask, (0,0,0))
    if root is not None:
        heapq.heappush(queue, (root, serial, library.full_mask, Plan((0,0,0))))
    labels = {library.full_mask: [(0,0,0)]}
    pending = None

    def check_time():
        if clock() >= started + timeout_seconds:
            raise _Deadline

    def global_lower():
        values = ([queue[0][0]] if queue else []) + ([pending] if pending is not None else [])
        if upper is not None:
            values.append(upper)
        return min(values) if values else None

    def mark_gaps(lower):
        if upper is None or lower is None:
            return
        for percentage, tolerance_value in [(5, Fraction(1,20)), (1, Fraction(1,100))]:
            key = f'gap_{percentage}_percent_seconds'
            if stats[key] is None and (upper == lower or (lower > 0 and upper <= (1+tolerance_value)*lower)):
                stats[key] = clock()-started

    reason = 'EXHAUSTED'
    try:
        while queue:
            lower = global_lower()
            mark_gaps(lower)
            if upper is not None and lower == upper:
                reason = 'BOUND_CLOSED'
                break
            if upper is not None and lower > 0 and eta > 0 and upper <= (1+eta)*lower:
                reason = 'GAP_TOLERANCE'
                break
            check_time()
            bound, _, remaining, prefix = heapq.heappop(queue)
            if upper is not None and bound >= upper:
                stats['bound_pruned'] += 1
                continue
            if any(r != prefix.resources and all(x <= y for x,y in zip(r,prefix.resources))
                   for r in labels.get(remaining, [])):
                stats['dominated'] += 1
                continue
            pending = bound
            if not remaining:
                verify(prefix)
                incumbent, upper = prefix, cost(prefix.resources,w)
                if stats['first_improvement_seconds'] is None:
                    stats['first_improvement_seconds'] = clock()-started
                pending = None
                continue
            stats['states'] += 1
            for cover, wave in canonical_waves(options, by_term, remaining, ancilla_max, check_time, stats):
                check_time()
                t,d,a = prefix.resources
                wt,wd,wa = wave.resources
                r = (t+wt, d+wd, max(a,wa))
                rest = remaining ^ cover
                child_bound = node_bound(rest,r)
                if child_bound is None:
                    continue
                child_bound = max(bound,child_bound)
                if upper is not None and child_bound >= upper:
                    stats['bound_pruned'] += 1
                    continue
                old = labels.setdefault(rest, [])
                if any(all(x <= y for x,y in zip(o,r)) for o in old):
                    stats['dominated'] += 1
                    continue
                labels[rest] = [o for o in old if not all(x <= y for x,y in zip(r,o))] + [r]
                serial += 1
                heapq.heappush(queue, (child_bound,serial,rest,Plan(r,prefix.waves+wave.waves)))
            pending = None
    except _Deadline:
        reason = 'TIMEOUT'
        stats['pending_expansion_at_timeout'] = pending is not None
    lower = global_lower()
    mark_gaps(lower)
    if upper is not None:
        status = 'OPTIMAL' if lower == upper else 'FEASIBLE'
    else:
        status = 'TIMEOUT' if reason == 'TIMEOUT' else 'INFEASIBLE'
    elapsed = clock()-started
    stats.update(seconds=elapsed, search_seconds=elapsed-stats['verification_seconds'],
                 queue_size=len(queue), bounds_cached=bounds.cache_info().currsize)
    return SearchResult(status, reason, incumbent, lower, upper, w, fp, stats)


def symbolic_search(library, coefficients, ancilla_max, depth_max=None, *,
                    timeout_seconds=60, tolerance='0', partial_pruning=True,
                    resolve_upfront=False, clock=time.perf_counter,
                    checkpoint=lambda stage: None, interleave=False,
                    coupled_bounds=False, target_cost=None):
    """Lazy refinement with streaming waves and certified pending-family bounds.

    Queue keys may lag shared refinements, which only makes them weaker. Prefix
    dominance is used only after every selected primitive is resolved. The active
    parent stays pending through refinement, generation, and finalist verification.
    ``checkpoint`` permits deterministic interruption tests (raise _Deadline).
    """
    from types import SimpleNamespace

    started = clock()
    _validate_limits(ancilla_max, depth_max)
    if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
        raise ValueError('timeout must be finite and nonnegative')
    w, eta = weights(coefficients), rational(tolerance)
    target = None if target_cost is None else rational(target_cost)
    if target is not None and target < 0:
        raise ValueError('target cost must be nonnegative')
    if eta < 0:
        raise ValueError('negative tolerance')
    fp = library.fingerprint(ancilla_max, depth_max)
    options = tuple(o for o in library.options if o.workspace <= ancilla_max)
    by_term = {i: tuple(o for o in options if o.terms & (1 << i))
               for i in range(len(library.terms))}
    stats = dict(states=0, waves=0, partial_waves=0, partial_pruned=0,
                 bound_pruned=0, dominated=0, queue_peak=1, label_peak=0,
                 first_incumbent_seconds=None, gap_5_percent_seconds=None,
                 gap_1_percent_seconds=None, pending_expansion_at_timeout=False,
                 partial_pruning=partial_pruning, resolve_upfront=resolve_upfront,
                 interleave=interleave, coupled_bounds=coupled_bounds,
                 target_cost=None if target is None else str(target),
                 first_improvement_seconds=None, open_tasks=0, scans=0,
                 interleaved_refinements=0, stale_rekeys=0)
    queue, serial, labels, cache = [], 0, {}, {}
    pending, incumbent, upper = Fraction(0), None, None
    reason = 'EXHAUSTED'
    eligible_cache = {}
    counts = {}
    for o in options:
        for r in o.requests:
            counts[r.key] = counts.get(r.key, 0) + 1

    def check(stage):
        checkpoint(stage)
        if clock() >= started + timeout_seconds:
            raise _Deadline

    def feasible(r):
        return r[2] <= ancilla_max and (depth_max is None or r[1] <= depth_max)

    def tail_bound(remaining):
        key = library.epoch, remaining
        if key not in cache:
            check('bounds')
            views = []
            for o in options:
                check('bound_scan')
                if o.terms & remaining == o.terms:
                    views.append(SimpleNamespace(terms=o.terms, boundary=o.boundary,
                                                 footprint=o.footprint, resources=library.evaluate(o).lower))
            cache[key] = (coupled_completion_bounds(library, remaining, views, ancilla_max,
                                                   lambda: check('bounds')) if coupled_bounds
                          else completion_bounds(library, remaining, views))
        return cache[key]

    def bound_for(remaining, r):
        tail = tail_bound(remaining)
        if tail is None:
            return None
        resources = (r[0]+tail[0], r[1]+tail[1], max(r[2], tail[2]))
        return cost(resources, w) if feasible(resources) else None

    def push(bound, remaining, waves, opened=None):
        nonlocal serial
        serial += 1
        heapq.heappush(queue, (bound, serial, remaining, waves, opened, library.epoch))
        stats['queue_peak'] = max(stats['queue_peak'], len(queue))

    def accept(waves):
        nonlocal incumbent, upper
        r = library.plan_resources(waves)
        if not feasible(r) or (upper is not None and cost(r, w) >= upper):
            return
        check('before_emission')
        plan = Plan(r, waves)
        lowered, proof = library.emit(plan, check_time=lambda: check('materialization'))
        if upper is not None and stats['first_improvement_seconds'] is None:
            stats['first_improvement_seconds'] = clock()-started
        incumbent, upper = plan, cost(r, w)
        stats['incumbent_emitted'] = estimate_resources(lowered).to_dict()
        stats['incumbent_verification'] = proof
        stats['incumbent_prediction'] = r
        if stats['first_incumbent_seconds'] is None:
            stats['first_incumbent_seconds'] = clock()-started

    def wave_generator(remaining, prefix):
        anchor = (remaining & -remaining).bit_length()-1
        boundary = min((o.boundary for o in by_term[anchor]), default=-1)
        eligible = [o for o in options if o.terms & remaining == o.terms and o.boundary == boundary]

        def extend(chosen, cover, footprint, r, first):
            check('partial_wave')
            stats['partial_waves'] += 1
            if partial_pruning:
                tail = tail_bound(remaining ^ cover)
                if tail is None:
                    stats['partial_pruned'] += 1
                    return
                # Remaining terms may JOIN this wave: use max, never sum, for D.
                relaxed = (prefix[0]+r[0]+tail[0], prefix[1]+max(r[1], tail[1]),
                           max(prefix[2], r[2], tail[2]))
                if not feasible(relaxed) or (upper is not None and cost(relaxed, w) >= upper):
                    stats['partial_pruned'] += 1
                    return
            stats['waves'] += 1
            yield cover, tuple(sorted(chosen))
            for j in range(first, len(eligible)):
                check('partial_wave_scan')
                o = eligible[j]
                if o.terms & cover or o.footprint & footprint or r[2]+o.workspace > ancilla_max:
                    continue
                t, d, a = library.evaluate(o).lower
                yield from extend((*chosen, o.id), cover | o.terms, footprint | o.footprint,
                                  (r[0]+t, max(r[1], d), r[2]+a), j+1)
        for o in by_term[anchor]:
            if o.terms & remaining == o.terms:
                yield from extend((o.id,), o.terms, o.footprint, library.evaluate(o).lower, 0)

    def open_bound(remaining, prefix, opened):
        r = library.plan_resources((opened.chosen,)) if opened.chosen else (0, 0, 0)
        if not feasible((prefix[0]+r[0], prefix[1]+r[1], max(prefix[2], r[2]))):
            return None
        if not partial_pruning:
            return bound_for(remaining, prefix)
        tail = tail_bound(remaining ^ opened.cover)
        if tail is None:
            return None
        relaxed = (prefix[0]+r[0]+tail[0], prefix[1]+max(r[1], tail[1]),
                   max(prefix[2], r[2], tail[2]))
        return cost(relaxed, w) if feasible(relaxed) else None

    def refine_one(ids):
        requests = {r.key: r for i in ids for r in library.unresolved(library.options[i])}
        if not requests:
            return False
        # Shared-use order is a heuristic only. All pruning uses certified costs.
        request = max(requests.values(), key=lambda r: (counts[r.key], r.key))
        library.refine(request, lambda: check('refinement'))
        stats['interleaved_refinements'] += 1
        return True

    def expand_open(remaining, waves, prefix, opened, bound):
        check('partial_wave')
        stats['open_tasks'] += 1
        if refine_one(opened.chosen):
            push(bound, remaining, waves, opened)
            return
        if opened.close_pending:
            check('wave_close')
            stats['waves'] += 1
            child_waves = waves + (tuple(sorted(opened.chosen)),)
            rest = remaining ^ opened.cover
            child_bound = bound_for(rest, library.plan_resources(child_waves))
            if child_bound is not None and (upper is None or child_bound < upper):
                push(max(bound, child_bound), rest, child_waves)
            push(bound, remaining, waves, OpenWave(opened.chosen, opened.cover,
                                                  opened.footprint, opened.cursor, False))
            return
        if remaining not in eligible_cache:
            anchor = (remaining & -remaining).bit_length()-1
            boundary = min((o.boundary for o in by_term[anchor]), default=-1)
            eligible_cache[remaining] = (
                tuple(o for o in by_term[anchor] if o.terms & remaining == o.terms),
                tuple(o for o in options if o.terms & remaining == o.terms and o.boundary == boundary))
        eligible = eligible_cache[remaining][bool(opened.chosen)]
        if opened.cursor >= len(eligible):
            return
        check('partial_wave_scan')
        stats['scans'] += 1
        o = eligible[opened.cursor]
        push(bound, remaining, waves, OpenWave(opened.chosen, opened.cover, opened.footprint,
                                              opened.cursor+1, False))
        r = library.plan_resources((opened.chosen,)) if opened.chosen else (0, 0, 0)
        if o.terms & opened.cover or o.footprint & opened.footprint or r[2]+o.workspace > ancilla_max:
            return
        child = OpenWave(opened.chosen+(o.id,), opened.cover | o.terms, opened.footprint | o.footprint,
                         opened.cursor+1 if opened.chosen else 0, True)
        stats['partial_waves'] += 1
        child_bound = open_bound(remaining, prefix, child)
        if child_bound is None or (upper is not None and child_bound >= upper):
            stats['partial_pruned'] += 1
            return
        # Refine before the sibling cursor resumes, even if its weaker bound
        # would otherwise keep every informative child behind a large expansion.
        refine_one(child.chosen)
        child_bound = open_bound(remaining, prefix, child)
        if child_bound is not None and (upper is None or child_bound < upper):
            push(max(bound, child_bound), remaining, waves, child)

    def global_lower():
        values = ([queue[0][0]] if queue else []) + ([pending] if pending is not None else [])
        if upper is not None:
            values.append(upper)
        return min(values) if values else None

    try:
        check('start')
        # A cheap direct seed; independent predicates can share a wave. A depth
        # violation rejects this seed only, not the construction family.
        seed_waves = []
        for i in range(len(library.terms)):
            o = next((o for o in by_term[i] if o.terms == 1 << i), None)
            if o is None:
                break
            library.resolve(o, lambda: check('refinement'))
            for wave in seed_waves:
                if all(library.options[j].boundary == o.boundary and
                       not library.options[j].footprint & o.footprint for j in wave):
                    wave.append(o.id)
                    break
            else:
                seed_waves.append([o.id])
        else:
            accept(tuple(tuple(wave) for wave in seed_waves))
        if resolve_upfront:
            for o in options:
                library.resolve(o, lambda: check('refinement'))
        root = bound_for(library.full_mask, (0, 0, 0))
        if root is not None:
            push(root, library.full_mask, ())
        pending = None
        while queue:
            lower = global_lower()
            if target is not None:
                if upper is not None and upper <= target:
                    reason = 'TARGET_REACHED'
                    break
            if upper is not None:
                for percentage in (5, 1):
                    key = f'gap_{percentage}_percent_seconds'
                    if stats[key] is None and (upper == lower or
                            lower > 0 and upper <= (1+Fraction(percentage, 100))*lower):
                        stats[key] = clock()-started
                if lower == upper or (eta > 0 and lower > 0 and upper <= (1+eta)*lower):
                    reason = 'BOUND_CLOSED' if lower == upper else 'GAP_TOLERANCE'
                    break
            check('queue')
            old_bound, _, remaining, waves, opened, epoch = heapq.heappop(queue)
            pending = old_bound
            resources = library.plan_resources(waves)
            bound = (open_bound(remaining, resources, opened) if opened is not None
                     else bound_for(remaining, resources))
            if bound is None or (upper is not None and bound >= upper):
                stats['bound_pruned'] += 1
                pending = None
                continue
            bound = max(bound, old_bound)
            if epoch != library.epoch and bound > old_bound:
                stats['stale_rekeys'] += 1
                push(bound, remaining, waves, opened)
                pending = None
                continue
            if opened is not None:
                expand_open(remaining, waves, resources, opened, bound)
                pending = None
                continue
            requests = {r.key: r for wave in waves for i in wave
                        for r in library.unresolved(library.options[i])}
            if requests:
                # Reuse ranking is heuristic; only proved lower bounds prune.
                request = max(requests.values(), key=lambda r: (counts[r.key], r.key))
                library.refine(request, lambda: check('refinement'))
                refined = bound_for(remaining, library.plan_resources(waves))
                if refined is not None:
                    push(max(bound, refined), remaining, waves)
                pending = None
                continue
            if not remaining:
                accept(waves)
                pending = None
                continue
            old = labels.setdefault(remaining, [])
            if any(all(x <= y for x, y in zip(r, resources)) for r in old):
                stats['dominated'] += 1
                pending = None
                continue
            labels[remaining] = [r for r in old if not all(x <= y for x, y in zip(resources, r))] + [resources]
            stats['label_peak'] = max(stats['label_peak'], sum(map(len, labels.values())))
            stats['states'] += 1
            if interleave:
                push(bound, remaining, waves, OpenWave())
                pending = None
                continue
            for cover, wave in wave_generator(remaining, resources):
                child_waves = waves + (wave,)
                rest = remaining ^ cover
                child_bound = bound_for(rest, library.plan_resources(child_waves))
                if child_bound is not None and (upper is None or child_bound < upper):
                    push(max(bound, child_bound), rest, child_waves)
            pending = None
    except _Deadline:
        reason = 'TIMEOUT'
        stats['pending_expansion_at_timeout'] = pending is not None
    lower = global_lower()
    status = ('OPTIMAL' if lower == upper else 'FEASIBLE') if upper is not None else (
        'TIMEOUT' if reason == 'TIMEOUT' else 'INFEASIBLE')
    stats.update(seconds=clock()-started, queue_size=len(queue), bounds_cached=len(cache),
                 symbolic=dict(library.stats), target_reached=target is not None and upper is not None and upper <= target)
    return SearchResult(status, reason, incumbent, lower, upper, w, fp, stats)
