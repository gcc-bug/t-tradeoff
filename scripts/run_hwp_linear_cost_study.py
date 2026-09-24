#!/usr/bin/env python3
"""Frozen cold-cache linear-cost comparison and separate finite-family references."""
from __future__ import annotations

import argparse
from fractions import Fraction
import importlib.metadata
from pathlib import Path
import statistics
import sys
import time

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from run_hwp_pareto import dump, load_program, sha
from run_hwp_symbolic_study import best, record, seed_plan
from collective_phase.hwp_cost_search import cost, symbolic_search, weights
from collective_phase.hwp_partition import partition_frontier
from collective_phase.hwp_pareto import _Deadline, baseline_frontiers, build_library, emit, frontier
from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.lowering import RotationSynthesizer
from collective_phase.resources import estimate_resources
from types import SimpleNamespace


def library_args(cfg):
    return dict(max_batch=cfg['max_batch'], max_terms=cfg['max_terms'],
                orderings=tuple(cfg['orderings']))


def selected(plans, query, cfg):
    return best(plans, weights(query['weights']), cfg)


def timed_trial(case, query, method, repeat, cfg):
    started = time.perf_counter()
    deadline = started + cfg['budget_seconds']
    row = dict(case=case['id'], query=query['id'], weights=query['weights'], method=method,
               repeat=repeat, status='TIMEOUT', reason='SETUP_TIMEOUT', L='0', U=None,
               plan=None, verification=None, emitted_resources=None,
               first_incumbent_seconds=None, scalar_certified_seconds=None,
               incumbent_history=[])

    def check():
        if time.perf_counter() >= deadline:
            raise _Deadline

    try:
        program = load_program(case)
        synth = RotationSynthesizer(seed=cfg['seed'])
        lib = SymbolicLibrary(program, cfg['total_error'], synth, **library_args(cfg))
        row['fingerprint'] = lib.fingerprint(cfg['ancilla'], cfg['depth'])
        check()
        w = weights(query['weights'])
        if method != 'native_partition':
            result = symbolic_search(lib, w, cfg['ancilla'], cfg['depth'],
                timeout_seconds=max(0., deadline-time.perf_counter()), interleave=True,
                integer_t_bounds=True, partition_bounds=method=='rounded_partition_progress',
                progress_order=method=='rounded_partition_progress', pareto_ties=False,
                tolerance='0')
            row.update(record(result))
            setup_seconds = result.stats['seconds']
            offset = time.perf_counter()-started-setup_seconds
            row['first_incumbent_seconds'] = (None if result.stats['first_incumbent_seconds'] is None
                else offset+result.stats['first_incumbent_seconds'])
            row['scalar_certified_seconds'] = (None if result.stats['scalar_certified_seconds'] is None
                else offset+result.stats['scalar_certified_seconds'])
            row['verification'] = result.stats.get('incumbent_verification')
            row['emitted_resources'] = result.stats.get('incumbent_emitted')
            row['incumbent_history'] = [dict(event, seconds=event['seconds']+offset)
                                        for event in result.stats['incumbent_history']]
        else:
            if case['kind'] != 'native':
                raise ValueError('native partition applied outside its domain')
            for option in lib.options:
                if option.workspace <= cfg['ancilla']:
                    lib.resolve(option, check)
            packed = SimpleNamespace(terms=lib.terms, groups=lib.groups,
                max_batch=lib.max_batch, options=tuple(SimpleNamespace(
                    id=o.id, terms=o.terms, group=o.group, boundary=o.boundary,
                    footprint=o.footprint, resources=lib.evaluate(o).lower)
                    for o in lib.options))

            def accept(plan):
                value = cost(plan.resources, w)
                if row['U'] is not None and value >= Fraction(row['U']):
                    return
                check()
                lowered, proof = lib.emit(plan, check_time=check)
                row.update(status='FEASIBLE', U=str(value), plan=plan.to_dict(),
                           verification=proof, emitted_resources=estimate_resources(lowered).to_dict())
                if row['first_incumbent_seconds'] is None:
                    row['first_incumbent_seconds'] = time.perf_counter()-started
                row['incumbent_history'].append(dict(seconds=time.perf_counter()-started,
                    cost=str(value), resources=plan.resources))
                check()

            accept(seed_plan(packed))
            result = partition_frontier(packed, cfg['ancilla'], cfg['depth'],
                timeout_seconds=max(0., deadline-time.perf_counter()), on_plan=accept)
            row['partition_stats'] = result.stats
            row['reason'] = 'EXHAUSTED' if result.complete else 'TIMEOUT'
            if result.complete:
                row['status'] = 'OPTIMAL' if row['U'] is not None else 'INFEASIBLE'
                row['L'] = row['U']
                row['scalar_certified_seconds'] = time.perf_counter()-started if row['U'] else None
    except _Deadline:
        row['reason'] = 'TIMEOUT'
    row['seconds'] = time.perf_counter()-started
    row['overrun_seconds'] = max(0., row['seconds']-cfg['budget_seconds'])
    row['gap'] = None if row['U'] is None or row['L'] is None else str(Fraction(row['U'])-Fraction(row['L']))
    return row


def reference(case, cfg, kind):
    started = time.perf_counter()
    deadline = started + cfg['reference_seconds']
    row = dict(case=case['id'], kind=kind, complete=False, plans=[],
               verification={}, emitted_resources={}, reason='SETUP_TIMEOUT')

    def check():
        if time.perf_counter() >= deadline:
            raise _Deadline

    try:
        program = load_program(case)
        lib = build_library(program, cfg['total_error'], RotationSynthesizer(seed=cfg['seed']),
                            check_time=check, **library_args(cfg))
        check()
        remaining = max(0., deadline-time.perf_counter())
        if kind == 'exact':
            result = (partition_frontier(lib, cfg['ancilla'], cfg['depth'], timeout_seconds=remaining)
                      if case['kind']=='native' else
                      frontier(lib, cfg['ancilla'], cfg['depth'], timeout_seconds=remaining))
            plans = result.plans
            row.update(complete=result.complete, stats=result.stats,
                       reason='EXHAUSTED' if result.complete else 'TIMEOUT')
        else:
            result = baseline_frontiers(lib, cfg['ancilla'], timeout_seconds=remaining)
            plans = [p for family in result['frontiers'].values() for p in family]
            plans.append(seed_plan(lib))
            row.update(complete=result['complete'], partitions=result['partitions'],
                       reason='EXHAUSTED' if result['complete'] else 'TIMEOUT')
        row['plans'] = [p.to_dict() for p in plans]
        for query in cfg['queries']:
            p = selected(plans, query, cfg)
            if p is None:
                continue
            check()
            lowered, proof = emit(lib, p, memory_cap_bytes=16*1024*1024 if case['kind']=='masks' else 1)
            row['verification'][query['id']] = proof
            row['emitted_resources'][query['id']] = estimate_resources(lowered).to_dict()
            check()
    except _Deadline:
        row['reason'] = 'TIMEOUT'
        row['complete'] = False
    row['seconds'] = time.perf_counter()-started
    row['overrun_seconds'] = max(0., row['seconds']-cfg['reference_seconds'])
    return row


def validate(data):
    refs = {(r['case'], r['kind']): r for r in data['references']}
    queries = {q['id']: q for q in data['config']['queries']}
    for row in data['samples']:
        exact = refs.get((row['case'], 'exact'))
        optimum = None
        if exact and exact['complete']:
            points = [tuple(p['resources']) for p in exact['plans']]
            optimum = min((cost(p, weights(row['weights'])) for p in points), default=None)
        if optimum is not None:
            assert row['L'] is None or Fraction(row['L']) <= optimum, row
            assert row['U'] is None or Fraction(row['U']) >= optimum, row
            if row['status']=='OPTIMAL':
                assert Fraction(row['U']) == optimum, row
        if row['U'] is not None:
            assert row['verification']['status'].startswith('verified_lowered_'), row
            assert Fraction(row['U']) == cost(row['plan']['resources'], weights(queries[row['query']]['weights']))
        assert row['gap'] is None or Fraction(row['gap']) >= 0, row


def render(data):
    cfg = data['config']
    refs = {(r['case'], r['kind']): r for r in data['references']}
    lines = ['# Mixed linear-cost HWP study', '',
        'New execution under the [frozen protocol](../docs/hwp-linear-cost-evaluation.md). '
        'J uses the supplied raw weights; depth is complete-wave depth. Emitted depth is retained '
        'in the raw resource records. Exactness is restricted to the declared finite family. '
        'Each timed result includes setup, refinement, search, and verified emission; imports '
        'and serialization are excluded. References are separate and were never used as timed seeds.', '',
        '| Input / weights | Best strong reference J | Exact family J* or incomplete | Method | U | L | Gap U-L | Selected (T,D,A) | Time s / optimal |',
        '|---|---:|---:|---|---:|---:|---:|---|---|']
    for case in cfg['cases']:
        exact, strong = refs[(case['id'],'exact')], refs[(case['id'],'batching')]
        for q in cfg['queries']:
            w = weights(q['weights'])
            epoints = [p['resources'] for p in exact['plans']]
            bpoints = [p['resources'] for p in strong['plans']]
            estar = min((cost(p,w) for p in epoints), default=None)
            bstar = min((cost(p,w) for p in bpoints), default=None)
            ecell = str(estar) if exact['complete'] else f'incomplete (best U={estar})'
            bcell = str(bstar) if strong['complete'] else f'incomplete (best U={bstar})'
            for method in cfg['methods']:
                if method=='native_partition' and case['kind']!='native':
                    continue
                rows = [r for r in data['samples'] if (r['case'],r['query'],r['method'])==
                        (case['id'],q['id'],method)]
                for r in rows:
                    tup = tuple(r['plan']['resources']) if r['plan'] else None
                    lines.append(f"| {case['id']} / {q['id']} {tuple(q['weights'])} | {bcell} | {ecell} | "
                        f"{method} #{r['repeat']+1} | {r['U']} | {r['L']} | {r['gap']} | {tup} | "
                        f"{r['seconds']:.3f} / {r['status']} |")
    lines += ['', 'Native partition is inapplicable to both overlap inputs. Incomplete reference '
        'incumbents are upper bounds only. Equal-cost tuples are equal primary-quality outcomes.', '',
        '| Input / query | Method | Verified incumbent / 3 | Exact optimum / 3 | Median elapsed s | Median time to J* s (successes / 3) |',
        '|---|---|---:|---:|---:|---|']
    for case in cfg['cases']:
        exact = refs[(case['id'],'exact')]
        for q in cfg['queries']:
            w = weights(q['weights'])
            optimum = min((cost(p['resources'],w) for p in exact['plans']),default=None) if exact['complete'] else None
            for method in cfg['methods']:
                if method=='native_partition' and case['kind']!='native':
                    continue
                rows = [r for r in data['samples'] if (r['case'],r['query'],r['method'])==
                        (case['id'],q['id'],method)]
                reached = [next((event['seconds'] for event in r['incumbent_history']
                           if Fraction(event['cost'])<=optimum), None) for r in rows] if optimum is not None else []
                reached = [t for t in reached if t is not None]
                exact_count = sum(optimum is not None and r['U'] is not None and Fraction(r['U'])==optimum for r in rows)
                times = f"{statistics.median(reached):.3f} ({len(reached)}/3)" if reached else 'n/a (0/3)'
                lines.append(f"| {case['id']} / {q['id']} | {method} | {sum(r['U'] is not None for r in rows)}/3 | "
                    f"{exact_count}/3 | {statistics.median(r['seconds'] for r in rows):.3f} | {times} |")
    lines += ['', f"Maximum timed overrun: {max(r['overrun_seconds'] for r in data['samples']):.3f}s. "
        'Cost gaps and completion are compared within each input and weight query only. '
        'The strong batching reference is a local construction comparator, not all published HWP methods.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/hwp-linear-cost-study.yaml')
    parser.add_argument('--output', default='results/hwp-linear-cost-study.json.gz')
    parser.add_argument('--report', default='reports/hwp-linear-cost-study.md')
    args = parser.parse_args()
    import pygridsynth
    cfg = yaml.safe_load((ROOT/args.config).read_text())
    paths = [*sorted((ROOT/'src/collective_phase').rglob('*.py')), Path(__file__),
             ROOT/args.config, ROOT/'scripts/run_hwp_pareto.py', ROOT/'scripts/run_hwp_symbolic_study.py']
    data = dict(config=cfg, hashes={str(p.relative_to(ROOT)):sha(p) for p in paths},
                environment={p:importlib.metadata.version(p) for p in ('numpy','pygridsynth','PyYAML')},
                samples=[], references=[])
    for case in cfg['cases']:
        for q in cfg['queries']:
            methods = [m for m in cfg['methods'] if m!='native_partition' or case['kind']=='native']
            for repeat in range(cfg['repeats']):
                for method in methods[repeat % len(methods):]+methods[:repeat % len(methods)]:
                    row = timed_trial(case,q,method,repeat,cfg)
                    data['samples'].append(row)
                    print(case['id'],q['id'],repeat,method,row['status'],row['U'],flush=True)
                    dump(ROOT/args.output,data)
        for kind in ('exact','batching'):
            row = reference(case,cfg,kind)
            data['references'].append(row)
            print(case['id'],kind,row['complete'],row['seconds'],flush=True)
            dump(ROOT/args.output,data)
    validate(data)
    data['validation'] = 'verified incumbents and cost/bounds checked against completed exact references'
    dump(ROOT/args.output,data)
    (ROOT/args.report).write_text(render(data))


if __name__ == '__main__':
    main()
