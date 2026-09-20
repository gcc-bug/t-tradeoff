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
