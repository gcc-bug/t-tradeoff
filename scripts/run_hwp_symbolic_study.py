#!/usr/bin/env python3
"""Frozen H1/H2 comparison; each timed method owns its cache and seed cost."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from fractions import Fraction
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from run_hwp_pareto import load_program, sha, dump
from collective_phase import hwp_pareto as eager_module
from collective_phase import hwp_symbolic as symbolic_module
from collective_phase.hwp_cost_search import Model, cost, search, symbolic_search, weights
from collective_phase.hwp_pareto import Plan, build_library, frontier, emit, baseline_frontiers
from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.lowering import RotationSynthesizer
from collective_phase.resources import estimate_resources


@contextmanager
def phase_metrics(memory=False):
    """Exclusive wall time and inclusive traced-heap peaks by phase.

    A separate memory run is kept out of timing samples. At nested phase changes
    the current parent's peak is saved before tracemalloc resets the peak.
    """
    from contextlib import ExitStack
    totals, peaks, stack = defaultdict(float), defaultdict(int), []
    if memory:
        tracemalloc.start()
    last = time.perf_counter()

    def account():
        nonlocal last
        now = time.perf_counter()
        totals[stack[-1] if stack else 'setup_search_other'] += now-last
        last = now
        if memory:
            peak = tracemalloc.get_traced_memory()[1]
            for name in stack or ['setup_search_other']:
                peaks[name] = max(peaks[name], peak)
            tracemalloc.reset_peak()

    def wrap(function, phase):
        def measured(*args, **kwargs):
            account()
            stack.append(phase)
            try:
                return function(*args, **kwargs)
            finally:
                account()
                stack.pop()
        return measured

    specs = [(RotationSynthesizer, 'synthesize', 'rotation_synthesis'),
             (eager_module, 'lower_candidate', 'lowering'),
             (eager_module, 'lower_candidate_with_rotations', 'lowering'),
             (eager_module, 'verify_lowered_circuit', 'verification'),
             (symbolic_module, 'lower_candidate_with_rotations', 'lowering'),
             (symbolic_module, 'verify_lowered_circuit', 'verification'),
             (SymbolicLibrary, '__init__', 'description'),
             (SymbolicLibrary, 'graph', 'graph'),
             (SymbolicLibrary, 'evaluate', 'summary'),
             (eager_module, 'canonical_waves', 'wave_generator_setup')]
    metrics = {'exclusive_seconds': totals, 'inclusive_heap_peak_bytes': peaks}
    with ExitStack() as context:
        for owner, name, phase in specs:
            context.enter_context(patch.object(owner, name, wrap(getattr(owner, name), phase)))
        try:
            yield metrics
        finally:
            account()
            if memory:
                peaks['total'] = max([tracemalloc.get_traced_memory()[1], *peaks.values()])
                tracemalloc.stop()


def seed_plan(lib):
    waves = []
    for i in range(len(lib.terms)):
        o = next(o for o in lib.options if o.terms == 1 << i)
        for wave in waves:
            if all(x.boundary == o.boundary and not x.footprint & o.footprint for x in wave):
                wave.append(o)
                break
        else:
            waves.append([o])
    return Plan((sum(o.resources[0] for wave in waves for o in wave),
                 sum(max(o.resources[1] for o in wave) for wave in waves), 0),
                tuple(tuple(o.id for o in wave) for wave in waves))


def best(plans, w, query):
    return min((p for p in plans if p.resources[2] <= query['ancilla'] and
                (query['depth'] is None or p.resources[1] <= query['depth'])),
               key=lambda p: (cost(p.resources,w),p.resources,p.waves), default=None)


def record(result):
    return dict(status=result.status, reason=result.reason,
                L=None if result.lower is None else str(result.lower),
                U=None if result.upper is None else str(result.upper),
                gap=None if result.absolute_gap is None else str(result.absolute_gap),
                plan=None if result.plan is None else result.plan.to_dict(),
                fingerprint=result.fingerprint, stats=result.stats)


def run_sequence(program, config, orderings, method, queries, scales, *, memory=False):
    synth = RotationSynthesizer(seed=config['seed'])
    start = time.perf_counter()
    records = []
    kwargs = dict(max_batch=config['max_batch'],max_terms=config['max_terms'],orderings=orderings)
    with phase_metrics(memory) as metrics:
        if method.startswith('symbolic'):
            lib = SymbolicLibrary(program,config['total_error'],synth,**kwargs)
            setup_seconds = time.perf_counter()-start
            for query in queries:
                w = tuple(Fraction(x)/s for x,s in zip(query['preference'],scales))
                result = symbolic_search(lib,w,query['ancilla'],query['depth'],
                    timeout_seconds=config['search_seconds'],
                    resolve_upfront=method=='symbolic_resolved',
                    partial_pruning=method!='symbolic_unpruned')
                records.append({'query':query['id'],'weights':list(map(str,w)),**record(result)})
            work = dict(lib.stats)
        else:
            lib = build_library(program,config['total_error'],synth,**kwargs)
            model = Model(lib)
            seed = seed_plan(lib)
            # Frontier acquisition is once per entire sequence, never per query.
            exact = (frontier(lib,config['ancilla_envelope'],timeout_seconds=config['frontier_seconds'])
                     if method=='frontier' else None)
            setup_seconds = time.perf_counter()-start
            emissions = 0
            for query in queries:
                w = tuple(Fraction(x)/s for x,s in zip(query['preference'],scales))
                if method=='guided':
                    result = search(model,w,query['ancilla'],query['depth'],seeds=[seed],
                                    timeout_seconds=config['search_seconds'])
                    row = record(result)
                    # search verifies its feasible seed and every improved incumbent.
                    emissions += int(result.stats['seed_upper'] is not None)
                    emissions += int(result.stats['first_improvement_seconds'] is not None)
                else:
                    tick = time.perf_counter()
                    p = best([*exact.plans,seed],w,query)
                    resources = proof = None
                    if p:
                        lowered,proof = emit(lib,p)
                        resources = estimate_resources(lowered).to_dict()
                        emissions += 1
                    u = cost(p.resources,w) if p else None
                    lower = u if exact.complete else Fraction(0)
                    row = dict(status=('OPTIMAL' if p else 'INFEASIBLE') if exact.complete else
                                      ('FEASIBLE' if p else 'TIMEOUT'), reason='DP',
                               L=None if lower is None else str(lower), U=None if u is None else str(u),
                               gap=None if u is None else str(u-lower), plan=p.to_dict() if p else None,
                               fingerprint=model.query_fingerprint(query['ancilla'],query['depth']),
                               stats=dict(seconds=time.perf_counter()-tick,
                                          incumbent_emitted=resources,incumbent_verification=proof))
                records.append({'query':query['id'],'weights':list(map(str,w)),**row})
            work = {'descriptors':len(lib.options),'templates_materialized':lib.stats['templates'],
                    'circuits_emitted':emissions,'circuits_verified':emissions,
                    'rotations_refined':len(synth._cache),'library':lib.stats,
                    'frontier':exact.stats if exact else None}
        seconds = time.perf_counter()-start
    return dict(seconds=seconds,setup_seconds=setup_seconds,work=work,phases=metrics,queries=records)


def inputs(config):
    old = yaml.safe_load((ROOT/config['development_config']).read_text())
    original = yaml.safe_load((ROOT/old['development_config']).read_text())
    development = original['cases'] + old['additional_cases']
    cases = development + config['additional_cases']
    queries = [dict(id=f"{limit['id']}:{i}",preference=pref,ancilla=limit['ancilla'],depth=limit['depth'])
               for limit in old['limits'] for i,pref in enumerate(old['preferences']+old['holdout_preferences'])]
    return cases, {c['id']: queries if c in development else config['additional_queries'] for c in cases}


def check_outcomes(samples, known):
    by_query = defaultdict(list)
    for sample in samples:
        for row in sample['queries']:
            by_query[sample['space'],row['query']].append(row)
    for (space,query), rows in by_query.items():
        optima = {Fraction(r['U']) for r in rows if r['status']=='OPTIMAL'}
        if space=='original' and query in known and known[query] is not None:
            optima.add(Fraction(known[query]))
        if len(optima)>1:
            raise AssertionError(f'contradictory optima {space}, {query}: {optima}')
        if optima:
            optimum = next(iter(optima))
            for row in rows:
                assert row['status']!='INFEASIBLE'
                assert row['L'] is None or Fraction(row['L'])<=optimum
                assert row['U'] is None or optimum<=Fraction(row['U'])
        if space=='original' and query in known and known[query] is None:
            assert all(row['U'] is None for row in rows)
        if space=='expanded' and query in known and known[query] is not None:
            assert all(row['L'] is None or Fraction(row['L'])<=Fraction(known[query]) for row in rows)


def save_witness(program, case_samples, config):
    """Replay a certified expanded-space improvement outside timed controllers."""
    for sample in case_samples:
        if sample['space'] != 'expanded':
            continue
        for row in sample['queries']:
            if row['U'] is None:
                continue
            old = [r for s in case_samples if s['space']=='original' for r in s['queries']
                   if r['query']==row['query'] and r['L'] is not None]
            if not old or Fraction(row['U']) >= max(Fraction(r['L']) for r in old):
                continue
            lib = SymbolicLibrary(program,config['total_error'],RotationSynthesizer(seed=config['seed']),
                max_batch=config['max_batch'],max_terms=config['max_terms'],
                orderings=tuple(config['spaces']['expanded']))
            plan = Plan(tuple(row['plan']['resources']),tuple(tuple(w) for w in row['plan']['waves']))
            lowered, proof = lib.emit(plan)
            witness = dict(case=program.id,query=row['query'],weights=row['weights'],
                old_lower=str(max(Fraction(r['L']) for r in old)),expanded_upper=row['U'],
                plan=plan.to_dict(),program=program.to_dict(),candidate=lowered.candidate.to_dict(),
                lowering=lowered.to_dict(),verification=proof,resources=estimate_resources(lowered).to_dict(),
                recipes=[dict(id=i,layout=lib.options[i].layout,ordering=lib.options[i].ordering,
                              masks=lib.options[i].local_masks) for w in plan.waves for i in w])
            dump(ROOT/'results/hwp-symbolic-witness.json.gz',witness)
            return {'case':program.id,'query':row['query'],'path':'results/hwp-symbolic-witness.json.gz'}
    return None


def render(summary):
    samples = summary['samples']
    lines = ['# HWP symbolic bounds: frozen comparison', '',
        'Costs certify only the enumerated unitary construction family, fixed normalized-term precision, '
        'and complete-wave depth. Ordinary emitted T-depth is recorded separately. '
        'All timings include setup, seed acquisition, failed search work, lowering, and verification. '
        'Three independent cache lifecycles are reported individually in the evidence.', '',
        '| Space / mode | Method | Total median seconds across cases | Certified optimal / queried samples |',
        '|---|---|---:|---:|']
    for space,mode,method in sorted({(s['space'],s['mode'],s['method']) for s in samples}):
        chosen = [s for s in samples if (s['space'],s['mode'],s['method'])==(space,mode,method)]
        cases = {s['case'] for s in chosen}
        total = sum(statistics.median(s['seconds']+s['input_seconds']+s['scale_seconds']
                                     for s in chosen if s['case']==c) for c in cases)
        rows = [q for s in chosen for q in s['queries']]
        lines.append(f"| {space} / {mode} | {method} | {total:.4f} | "
                     f"{sum(r['status']=='OPTIMAL' for r in rows)} / {len(rows)} |")
    lines += ['', 'The table above includes interrupted queries; unequal completion rates are not equal-quality speedups.', '',
              '| Original space, matched complete outcomes | Cases | Frontier median s | Symbolic median s |',
              '|---|---:|---:|---:|']
    for mode in ('cold','warm'):
        matched=[]
        for c in sorted({s['case'] for s in samples}):
            pair={m:[s for s in samples if s['space']=='original' and s['mode']==mode and
                     s['case']==c and s['method']==m] for m in ('frontier','symbolic')}
            if all(pair.values()) and all(q['status'] in {'OPTIMAL','INFEASIBLE'}
                    for ss in pair.values() for s in ss for q in s['queries']):
                matched.append(pair)
        totals = [sum(statistics.median(s['seconds']+s['input_seconds']+s['scale_seconds'] for s in p[m])
                      for p in matched) for m in ('frontier','symbolic')]
        lines.append(f'| {mode} | {len(matched)} | {totals[0]:.4f} | {totals[1]:.4f} |')
    wins=[]
    lines += ['', '| Circuit quality under matched constraints | Verified strict wins over old certified optimum |',
              '|---|---:|']
    for c in sorted({s['case'] for s in samples}):
        rows = [s for s in samples if s['case']==c]
        old, new = defaultdict(list), defaultdict(list)
        for sample in rows:
            for r in sample['queries']:
                (old if sample['space']=='original' else new)[r['query']].append(r)
        count=0
        for query in old.keys() & new.keys():
            certified=[Fraction(r['L']) for r in old[query] if r['L'] is not None]
            feasible=[Fraction(r['U']) for r in new[query] if r['U'] is not None]
            if certified and feasible and min(feasible)<max(certified):
                count+=1
                wins.append((c,query))
        lines.append(f'| {c} | {count} |')
    lines += ['', f'H2: {len(wins)} distinct case/query improvements are certified against the old-space bound. '
              'A zero count does not establish that every larger arithmetic family is unhelpful.', '',
              'H1 must be read from the matched-outcome table and individual repetitions, not emission counts. '
              'The full-frontier baseline is charged once in warm sequences. Deadline overruns can include one '
              'atomic synthesis or verification call. DP interruptions retain feasible plans and use the safe '
              'lower bound zero; their incomplete frontier is never called an optimum.', '',
              'The separate memory samples use tracemalloc: phase peaks are inclusive absolute Python heap '
              'high-water marks (nested work is included); timing phase buckets are exclusive. Native allocator '
              'memory inside numerical libraries is not covered. Memory runs are excluded from timing aggregates. '
              'Setup/search/other includes descriptor enumeration in the eager path and wave enumeration in both paths.', '',
              'Strong uniform/per-group batching frontiers, including both arithmetic orderings, are measured '
              'separately with their own completion flags. An interrupted reference is not a certified optimum. '
              'No post-optimization or publication step was performed.', '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='configs/hwp-symbolic-study.yaml')
    parser.add_argument('--cases',nargs='*')
    parser.add_argument('--output',default='results/hwp-symbolic-study.json.gz')
    parser.add_argument('--report',default='reports/hwp-symbolic-study.md')
    parser.add_argument('--skip-memory',action='store_true')
    args=parser.parse_args()
    config_path=ROOT/args.config
    config=yaml.safe_load(config_path.read_text())
    cases, query_sets=inputs(config)
    if args.cases:
        cases=[c for c in cases if c['id'] in args.cases]
        if len(cases)!=len(args.cases):
            raise ValueError('unknown or repeated case')
    frozen=json.loads((ROOT/config['development_oracle']).read_text())
    summary=dict(config=config,config_sha256=sha(config_path),selected_cases=[c['id'] for c in cases],
                 source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src').rglob('*.py'))},
                 runner_sha256=sha(__file__),versions={name:importlib.metadata.version(name)
                     for name in ('numpy','pygridsynth','PyYAML')},samples=[],memory_samples=[],baselines=[])
    for case in cases:
        tick=time.perf_counter()
        program=load_program(case)
        input_seconds=time.perf_counter()-tick
        queries=query_sets[case['id']]
        previous=[r for r in frozen['queries'] if r['case']==case['id']]
        tick=time.perf_counter()
        if previous:
            scales=previous[0]['scales']
            known={q['id']:next(r['optimum_cost'] for r in previous
                if r['preference']==q['preference'] and r['limits']['ancilla']==q['ancilla']
                and r['limits']['depth']==q['depth']) for q in queries}
        else:
            direct=build_library(program,config['total_error'],RotationSynthesizer(seed=config['seed']),
                                 max_batch=1,max_terms=config['max_terms'])
            p=seed_plan(direct)
            scales=[max(1,p.resources[0]),max(1,p.resources[1]),max(1,config['ancilla_envelope'])]
            known={}
        scale_seconds=time.perf_counter()-tick
        case_samples=[]
        for space,orderings in config['spaces'].items():
            for mode in ('cold','warm'):
                selected=[queries[config['cold_query_index']]] if mode=='cold' else queries
                for method in config['methods']:
                    for repetition in range(config['repeats']):
                        sample=run_sequence(program,config,tuple(orderings),method,selected,scales)
                        sample.update(case=case['id'],space=space,mode=mode,method=method,
                                      repetition=repetition,scales=scales,input_seconds=input_seconds,
                                      scale_seconds=scale_seconds)
                        case_samples.append(sample)
                    print(f"{case['id']} {space} {mode} {method}: three samples",flush=True)
            # Strong batching references are independent of timed H1 controllers.
            tick=time.perf_counter()
            baseline_lib=build_library(program,config['total_error'],RotationSynthesizer(seed=config['seed']),
                max_batch=config['max_batch'],max_terms=config['max_terms'],orderings=tuple(orderings))
            refs=baseline_frontiers(baseline_lib,config['ancilla_envelope'],
                                    timeout_seconds=config['baseline_seconds'])
            summary['baselines'].append(dict(case=case['id'],space=space,complete=refs['complete'],
                seconds=time.perf_counter()-tick,partitions=refs['partitions'],frontiers={
                    name:[p.to_dict() for p in plans] for name,plans in refs['frontiers'].items()}))
        check_outcomes(case_samples,known)
        summary['samples'].extend(case_samples)
        if not summary.get('witness'):
            summary['witness'] = save_witness(program,case_samples,config)
        if not args.skip_memory:
            for method in config['methods']:
                # Memory diagnostics intentionally use one cold original-space query.
                sample=run_sequence(program,config,('staged',),method,[queries[0]],scales,memory=True)
                summary['memory_samples'].append(dict(case=case['id'],method=method,**sample))
        dump(ROOT/args.output,summary)
        (ROOT/args.report).parent.mkdir(parents=True,exist_ok=True)
        (ROOT/args.report).write_text(render(summary))
    print(f'Evidence: {args.output}; report: {args.report}',flush=True)


if __name__=='__main__':
    main()
