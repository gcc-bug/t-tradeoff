#!/usr/bin/env python3
"""Constrained native-nine ablations, independent partitions and coupled probes."""
from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import importlib.metadata
from pathlib import Path
import statistics
import sys
import time

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from run_hwp_pareto import dump, load_program, sha
from run_hwp_symbolic_study import record, seed_plan, best
from collective_phase.hwp_cost_search import symbolic_search, completion_bounds, partition_count_bound, cost, weights
from collective_phase.hwp_partition import partition_frontier
from collective_phase.hwp_pareto import build_library, frontier, emit, baseline_frontiers, _Deadline
from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.lowering import RotationSynthesizer
from collective_phase.resources import estimate_resources
from types import SimpleNamespace


def flags(method):
    return dict(interleave=True, pareto_ties=method != 'original',
                progress_order=method in {'ties_progress', 'combined'},
                partition_bounds=method in {'ties_partition', 'combined'})


def trial(case, cfg, method, budget, mode, query=None):
    query = cfg['query'] if query is None else query
    start = time.perf_counter()
    deadline = start + budget
    def check():
        if time.perf_counter() >= deadline:
            raise _Deadline
    # SymbolicLibrary checks after atomic synthesis, retaining its result even
    # when the call overruns. Eager setup likewise checks between operations.
    synth = RotationSynthesizer(seed=cfg['seed'])
    lib = None
    rows = []
    sequence = [cfg['warmup'], query] if mode == 'warm' else [query]
    for index, q in enumerate(sequence):
        tick = start if index == 0 else time.perf_counter()
        deadline = tick + budget
        row = dict(status='TIMEOUT', reason='SETUP_TIMEOUT', L='0', U=None, plan=None, stats={})
        setup = 0.
        try:
            if lib is None:
                t = time.perf_counter()
                program = load_program(case)
                kwargs = dict(max_batch=cfg['max_batch'], max_terms=cfg['max_terms'], orderings=tuple(cfg['orderings']))
                lib = (build_library(program, cfg['total_error'], synth, check_time=check, **kwargs)
                       if method == 'batching' else
                       SymbolicLibrary(program, cfg['total_error'], synth, **kwargs))
                setup = time.perf_counter()-t
            check()
            w = weights(q['weights'])
            if method not in {'partition', 'batching'}:
                result = symbolic_search(lib, w, q['ancilla'], q['depth'],
                                         timeout_seconds=max(0., deadline-time.perf_counter()), **flags(method))
                row = record(result)
                # Search-relative timestamps become query-relative for all methods.
                for event in row['stats']['incumbent_history']:
                    event['seconds'] += setup
                for key in ['scalar_certified_seconds', 'first_incumbent_seconds', 'first_improvement_seconds']:
                    if row['stats'][key] is not None:
                        row['stats'][key] += setup
            else:
                row['stats'].update(incumbent_history=[], endpoint_certified=False, scalar_certified_seconds=None)
                if method == 'partition':
                    # Share the compact cost representation, not the controller:
                    # synthesize only individually eligible blocks and emit only
                    # incumbents. Eagerly lowering every template would handicap
                    # this specialized enumeration baseline with irrelevant work.
                    for option in lib.options:
                        if option.workspace <= q['ancilla']:
                            lib.resolve(option, check)
                    packed = SimpleNamespace(terms=lib.terms, groups=lib.groups, max_batch=lib.max_batch,
                        options=tuple(SimpleNamespace(id=o.id, terms=o.terms, group=o.group,
                            boundary=o.boundary, footprint=o.footprint, resources=lib.evaluate(o).lower) for o in lib.options))
                else:
                    packed = lib
                def accept(plan):
                    if plan.resources[2] > q['ancilla'] or (q['depth'] is not None and plan.resources[1] > q['depth']):
                        return
                    value = cost(plan.resources, w)
                    if row['U'] is not None and (value, plan.resources) >= (Fraction(row['U']), tuple(row['plan']['resources'])):
                        return
                    check()
                    lowered, proof = lib.emit(plan, check_time=check) if method == 'partition' else emit(lib, plan)
                    row.update(status='FEASIBLE', U=str(value), plan=plan.to_dict())
                    row['stats'].update(incumbent_verification=proof, incumbent_emitted=estimate_resources(lowered).to_dict())
                    row['stats']['incumbent_history'].append(dict(seconds=time.perf_counter()-tick, cost=str(value), resources=plan.resources))
                    check()
                accept(seed_plan(packed))
                if method == 'partition':
                    result = partition_frontier(packed, q['ancilla'], q['depth'],
                                                timeout_seconds=max(0., deadline-time.perf_counter()), on_plan=accept)
                    row['stats'].update(result.stats)
                    row['reason'] = 'EXHAUSTED' if result.complete else 'TIMEOUT'
                    if result.complete:
                        row['status'] = 'OPTIMAL' if row['U'] is not None else 'INFEASIBLE'
                        row['L'] = row['U']
                        row['stats']['endpoint_certified'] = row['U'] is not None
                        row['stats']['scalar_certified_seconds'] = time.perf_counter()-tick if row['U'] else None
                else:
                    result = baseline_frontiers(lib, q['ancilla'], timeout_seconds=max(0., deadline-time.perf_counter()))
                    row.update(reason='RESTRICTED_BATCHING', reference_complete=result['complete'])
                    row['stats'].update(partitions=result['partitions'])
                    p = best([p for ps in result['frontiers'].values() for p in ps], w, q)
                    if p is not None:
                        accept(p)
        except _Deadline:
            if lib is None:
                setup = time.perf_counter()-tick
            row['reason'] = 'TIMEOUT'
        elapsed = time.perf_counter()-tick
        row.update(query=q, seconds=elapsed, setup_seconds=setup, overrun_seconds=max(0., elapsed-budget))
        rows.append(row)
    return dict(case=case['id'], method=method, mode=mode, budget=budget, queries=rows)


def reference(case, cfg, ancilla, depth):
    program = load_program(case)
    lib = build_library(program, cfg['total_error'], RotationSynthesizer(seed=cfg['seed']),
                        max_batch=cfg['max_batch'], orderings=tuple(cfg['orderings']))
    exact = frontier(lib, ancilla, depth, timeout_seconds=cfg['reference_seconds'])
    part = partition_frontier(lib, ancilla, depth, timeout_seconds=cfg['reference_seconds'])
    assert part.complete
    if exact.complete:
        assert {p.resources for p in exact.plans} == {p.resources for p in part.plans}
    batch = baseline_frontiers(lib, ancilla, timeout_seconds=cfg['reference_seconds'])
    batch_plans = [p for ps in batch['frontiers'].values() for p in ps if depth is None or p.resources[1] <= depth]
    proofs = [emit(lib, p)[1] for p in part.plans]
    return dict(case=case['id'], ancilla=ancilla, depth=depth,
                full_complete=exact.complete, full_stats=exact.stats,
                full_frontier=[p.to_dict() for p in exact.plans],
                partition_complete=part.complete, partition_stats=part.stats,
                partition_frontier=[p.to_dict() for p in part.plans], verification=proofs,
                batching_complete=batch['complete'], batching_frontier=[p.to_dict() for p in batch_plans]), lib, part


def diagnostics(case, cfg, lib, part):
    witness = min(part.plans, key=lambda p: p.resources)
    options = [SimpleNamespace(terms=o.terms, group=o.group, resources=o.resources)
               for o in lib.options if o.resources[2] <= cfg['query']['ancilla']]
    trace, cover = [], 0
    for option_id in (None, *witness.waves[0]):
        if option_id is not None:
            cover |= lib.options[option_id].terms
        remaining = lib.full_mask ^ cover
        trace.append(dict(cover=cover, remaining=remaining, fractional_tail=list(map(str, completion_bounds(lib, remaining, options))),
                          partition_tail=partition_count_bound(options, remaining)))
    rows = []
    for method in ('original', 'ties', 'combined'):
        sym = SymbolicLibrary(load_program(case), cfg['total_error'], RotationSynthesizer(seed=cfg['seed']),
                              max_batch=cfg['max_batch'], orderings=tuple(cfg['orderings']))
        for wave in witness.waves:
            for i in wave:
                assert (sym.options[i].terms, sym.options[i].layout, sym.options[i].ordering) == (
                    lib.options[i].terms, lib.options[i].layout, lib.options[i].ordering)
        result = symbolic_search(sym, weights(cfg['query']['weights']), cfg['query']['ancilla'], cfg['query']['depth'],
                                 seeds=(witness,), timeout_seconds=3, **flags(method))
        rows.append(dict(method=method, **record(result)))
    return dict(witness=witness.to_dict(), replay=trace, seeded_budget_seconds=3, seeded=rows,
                note='Diagnostic only; seeds are reverified and never supplied to timed comparisons.')


def validate(samples, references):
    refs = {(r['case'], r['ancilla'], r['depth']): r for r in references}
    for sample in samples:
        row = sample['queries'][-1]
        q = row['query']
        ref = refs[sample['case'], q['ancilla'], q['depth']]
        points = [tuple(p['resources']) for p in ref['partition_frontier']]
        w = weights(q['weights'])
        optimum = min((cost(p, w) for p in points), default=None)
        expected = min(points, key=lambda r: (cost(r, w), r), default=None)
        if optimum is None:
            assert row['U'] is None, sample
        else:
            assert row['status'] != 'INFEASIBLE'
            assert row['L'] is None or Fraction(row['L']) <= optimum
            assert row['U'] is None or Fraction(row['U']) >= optimum
            if row['status'] == 'OPTIMAL':
                assert Fraction(row['U']) == optimum
            if row['stats'].get('endpoint_certified'):
                assert tuple(row['plan']['resources']) == expected
        if row['U'] is not None:
            assert row['stats']['incumbent_verification']['status'].startswith('verified_lowered_')
            assert tuple(row['plan']['resources']) in points or not row['stats'].get('endpoint_certified')


def report(data, path):
    lines = ['# Constrained nine-rotation study', '',
             'All times include setup, search, synthesis and incumbent verification. Imports/startup and serialization are excluded. '
             'Cold means a fresh cache and a constrained query; warm first pays a separate equal-budget count query. '
             'OPTIMAL certifies scalar cost only; endpoint completion separately certifies the lexicographically smallest optimal resource tuple. '
             'Depth below is complete-wave depth, not the separately recorded emitted-circuit depth.', '',
             '| Cache | Budget s | Method | T=354 / trials | Endpoint certified / trials | Final tuples | Median time to T≤354 s | Median query s |',
             '|---|---:|---|---:|---:|---|---:|---:|']
    for mode in data['config']['modes']:
        for budget in data['config']['budgets_seconds']:
            for method in data['config']['methods']:
                rows = [s['queries'][-1] for s in data['samples'] if (s['mode'], s['budget'], s['method']) == (mode, budget, method)]
                times = [next((e['seconds'] for e in r['stats'].get('incumbent_history', []) if Fraction(e['cost']) <= 354), None) for r in rows]
                reached = [t for t in times if t is not None]
                tuples = sorted({str(tuple(r['plan']['resources'])) if r['plan'] else 'None' for r in rows})
                median = f'{statistics.median(reached):.4f}' if reached else '—'
                lines.append(f"| {mode} | {budget} | {method} | {len(reached)}/{len(rows)} | "
                             f"{sum(r['stats'].get('endpoint_certified',False) for r in rows)}/{len(rows)} | "
                             f"{'; '.join(tuples)} | {median} | {statistics.median(r['seconds'] for r in rows):.4f} |")
    lines += ['', 'Time-to-target medians include successful trials only; the success fraction alongside them is mandatory. '
              'Do not interpret unequal completion as an equal-quality speedup.', '',
              'The partition comparator uses integer size partitions and independent exact wave packing after checking exchangeability. '
              'It covers the supplied native family, including the coupled disjoint-group probes, but rejects overlapping predicates. '
              'Strong batching remains a restricted comparator.', '',
              '| Coupled case | Ancillas | Depth cap | Reference optimum | Original | Combined | Partition | Strong batching |',
              '|---|---:|---:|---|---|---|---|---|']
    indexed = {(s['case'], s['queries'][-1]['query']['ancilla'], s['queries'][-1]['query']['depth'], s['method']): s['queries'][-1]
               for s in data['coupled_samples']}
    for ref in data['references'][1:]:
        optimum = min((tuple(p['resources']) for p in ref['partition_frontier']), default=None)
        cells = []
        for method in ('original', 'combined', 'partition', 'batching'):
            r = indexed[ref['case'], ref['ancilla'], ref['depth'], method]
            cells.append(f"{tuple(r['plan']['resources']) if r['plan'] else None} ({r['status']})")
        lines.append(f"| {ref['case']} | {ref['ancilla']} | {ref['depth']} | {optimum} | " + ' | '.join(cells) + ' |')
    all_rows = [r for s in data['samples']+data['coupled_samples'] for r in s['queries']]
    lines += ['', f"Maximum deadline overrun: {max(r['overrun_seconds'] for r in all_rows):.4f}s. Atomic calls are charged.", '',
              'Raw records include complete references, verified plans, incumbent histories, lower/upper bounds, label/queue peaks, '
              'source/config hashes, warm-up outcomes, and separately labeled witness/seed diagnostics. '
              'This is a finite construction-family experiment, not a published-HWP superiority or global circuit-optimality claim.', '']
    path.write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/hwp-nine-study.yaml')
    parser.add_argument('--output', default='results/hwp-nine-study.json.gz')
    parser.add_argument('--report', default='reports/hwp-nine-study.md')
    args = parser.parse_args()
    # Import backend dependencies before clocks, without warming synthesis caches.
    import pygridsynth
    cfg = yaml.safe_load((ROOT/args.config).read_text())
    paths = [*sorted((ROOT/'src/collective_phase').rglob('*.py')), Path(__file__), ROOT/args.config,
             ROOT/'scripts/run_hwp_pareto.py', ROOT/'scripts/run_hwp_symbolic_study.py']
    data = dict(config=cfg, hashes={str(p.relative_to(ROOT)): sha(p) for p in paths},
                environment={p: importlib.metadata.version(p) for p in ('numpy', 'pygridsynth', 'PyYAML')},
                samples=[], references=[], coupled_samples=[])
    output = ROOT/args.output
    for budget in cfg['budgets_seconds']:
        for mode in cfg['modes']:
            for repeat in range(cfg['repeats']):
                methods = cfg['methods'][repeat:] + cfg['methods'][:repeat]
                for method in methods:
                    result = trial(cfg['case'], cfg, method, budget, mode)
                    result['repeat'] = repeat
                    data['samples'].append(result)
                    row = result['queries'][-1]
                    print(budget, mode, repeat, method, row['status'], row['U'], row['stats'].get('endpoint_certified'), flush=True)
                dump(output, data)
    ref, lib, part = reference(cfg['case'], cfg, cfg['query']['ancilla'], cfg['query']['depth'])
    data['references'].append(ref)
    data['diagnostics'] = diagnostics(cfg['case'], cfg, lib, part)
    dump(output, data)
    for case in cfg['coupled_cases']:
        for ancilla in cfg['coupled_ancillas']:
            for depth in cfg['coupled_depths']:
                q = dict(id='coupled', weights=['1', '0', '0'], ancilla=ancilla, depth=depth)
                for method in ('original', 'combined', 'partition', 'batching'):
                    data['coupled_samples'].append(trial(case, cfg, method, cfg['coupled_budget'], 'cold', q))
                ref, _, _ = reference(case, cfg, ancilla, depth)
                data['references'].append(ref)
                print(case['id'], ancilla, depth, 'references complete', ref['full_complete'], flush=True)
                dump(output, data)
    validate(data['samples']+data['coupled_samples'], data['references'])
    data['validation'] = 'all recorded incumbents verified; bounds and endpoint claims agree with completed references'
    dump(output, data)
    report(data, ROOT/args.report)


if __name__ == '__main__':
    main()
