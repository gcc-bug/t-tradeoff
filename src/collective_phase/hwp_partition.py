"""Independent size-partition baseline for disjoint native rotations.

Within an equal-angle group, singleton predicates are exchangeable. Enumerate
integer block-size partitions and local Pareto recipes, then exactly pack those
blocks into complete waves. No production wave enumerator or symbolic bound is
used. This covers the full supplied library only on the checked native domain;
shared/overlapping data predicates are explicitly rejected.
"""
from functools import lru_cache
from itertools import combinations, product
import math
import time

from .hwp_pareto import Plan, FrontierResult, pareto, _Deadline, _validate_limits


def partition_frontier(library, ancilla_max, depth_max=None, *, timeout_seconds=60,
                       on_plan=lambda plan: None):
    """Exact native-family frontier; ``on_plan`` lets callers verify incumbents.

    Setup, partition enumeration and scheduling obey the same deadline. Caller
    verification is charged through the callback; only completed plans escape.
    Every group's subset resource menus are checked before symmetry reduction.
    """
    _validate_limits(ancilla_max, depth_max)
    if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
        raise ValueError('timeout must be finite and nonnegative')
    masks = [t.mask for t in library.terms]
    if any(m.bit_count() != 1 for m in masks) or len(set(masks)) != len(masks):
        raise ValueError('partition baseline requires disjoint singleton predicates')
    started = time.perf_counter()
    stats = dict(partitions=0, schedules=0, labels_considered=0, peak_labels_per_state=0,
                 ancilla_max=ancilla_max, depth_max=depth_max,
                 domain='disjoint native singleton predicates; checked exchangeable menus')
    incumbents = []

    def check():
        if time.perf_counter() >= started + timeout_seconds:
            raise _Deadline

    def retain(plan):
        nonlocal incumbents
        if depth_max is not None and plan.resources[1] > depth_max:
            return
        if any(all(a <= b for a, b in zip(p.resources, plan.resources)) for p in incumbents):
            return
        on_plan(plan)
        incumbents = pareto([*incumbents, plan])

    @lru_cache(None)
    def schedules(shapes):
        check()
        stats['schedules'] += 1
        if not shapes:
            return (Plan((0, 0, 0)),)
        # Local indices rather than global option IDs keep this cache independent
        # of which exchangeable data wires received each size partition.
        boundary = min(s[0] for s in shapes)
        anchor = next(i for i, s in enumerate(shapes) if s[0] == boundary)
        others = [i for i, s in enumerate(shapes) if s[0] == boundary and i != anchor]
        labels = []
        for size in range(len(others) + 1):
            for extra in combinations(others, size):
                check()
                wave = (anchor, *extra)
                workspace = sum(shapes[i][3] for i in wave)
                if workspace > ancilla_max:
                    continue
                remaining = tuple(i for i in range(len(shapes)) if i not in wave)
                wt = sum(shapes[i][1] for i in wave)
                wd = max(shapes[i][2] for i in wave)
                for tail in schedules(tuple(shapes[i] for i in remaining)):
                    r = (wt + tail.resources[0], wd + tail.resources[1], max(workspace, tail.resources[2]))
                    if depth_max is None or r[1] <= depth_max:
                        waves = (wave,) + tuple(tuple(remaining[i] for i in w) for w in tail.waves)
                        labels.append(Plan(r, waves))
                        stats['labels_considered'] += 1
                if len(labels) > 256:
                    labels = pareto(labels)
        result = tuple(pareto(labels))
        stats['peak_labels_per_state'] = max(stats['peak_labels_per_state'], len(result))
        return result

    try:
        check()
        menus = {}
        for option in library.options:
            check()
            if option.resources[2] <= ancilla_max:
                menus.setdefault((option.group, option.terms), []).append(option)
        group_choices = []
        for g, indices in enumerate(library.groups):
            # Check every subset, including missing recipes, before quotienting
            # by term identity. This prevents accidental exactness on a subset.
            for size in range(1, min(library.max_batch, len(indices)) + 1):
                expected = None
                for subset in combinations(indices, size):
                    check()
                    mask = sum(1 << i for i in subset)
                    options = menus.get((g, mask), [])
                    signature = {(o.boundary, o.resources) for o in options}
                    if expected is not None and signature != expected:
                        raise ValueError('nonexchangeable resource menus in native group')
                    expected = signature
            def partitions(rest, minimum=1):
                check()
                if not rest:
                    yield ()
                    return
                for size in range(minimum, min(library.max_batch, len(rest)) + 1):
                    mask = sum(1 << i for i in rest[:size])
                    local = pareto(Plan(o.resources, ((o.id,),)) for o in menus.get((g, mask), []))
                    for tail in partitions(rest[size:], size):
                        for p in local:
                            yield (p.waves[0][0],) + tail
            group_choices.append(tuple(partitions(indices)))
        for selected in product(*group_choices):
            check()
            ids = tuple(i for group in selected for i in group)
            shapes = tuple((library.options[i].boundary, *library.options[i].resources) for i in ids)
            stats['partitions'] += 1
            for p in schedules(shapes):
                retain(Plan(p.resources, tuple(tuple(ids[i] for i in wave) for wave in p.waves)))
        complete = True
    except _Deadline:
        complete = False
    stats.update(seconds=time.perf_counter() - started, cache_hits=schedules.cache_info().hits)
    status = ('OPTIMAL' if incumbents else 'INFEASIBLE') if complete else ('FEASIBLE' if incumbents else 'TIMEOUT')
    return FrontierResult(status, incumbents, complete, stats)
