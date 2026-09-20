#!/usr/bin/env python3
"""Frozen cost-query study, using the original library and circuit schemas."""
from __future__ import annotations
import time
PROCESS_STARTED = time.perf_counter()
import argparse
from fractions import Fraction
import importlib.metadata
import json
import hashlib
import statistics
from pathlib import Path
import subprocess
import sys
import time
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from run_hwp_pareto import load_program, base_plans, dump, sha
from collective_phase.hwp_pareto import build_library, frontier, baseline_frontiers, pareto, emit
from collective_phase.lowering import RotationSynthesizer
from collective_phase.hwp_cost_search import Model, CertifiedInequality, search
from collective_phase.resources import estimate_resources


def cost(resources, weights):
    return sum(w * r for w, r in zip(weights, resources))


def best(plans, weights, limits):
    return min((p for p in plans if p.resources[2] <= limits['ancilla'] and
                (limits['depth'] is None or p.resources[1] <= limits['depth'])),
               key=lambda p: (cost(p.resources, weights), p.resources, p.waves), default=None)


def diagnosis(config, config_path):
    previous = json.loads((ROOT / 'results/hwp-pareto-study.json').read_text())
    mismatches = [p for p, h in previous['source_hashes'].items()
                  if __import__('hashlib').sha256(subprocess.check_output(
                      ['git', 'show', f"{config['base_revision']}:{p}"], cwd=ROOT)).hexdigest() != h]
    if mismatches:
        raise ValueError(f'original study source changed: {mismatches}')
    cases = yaml.safe_load((ROOT / config['development_config']).read_text())['cases'] + config['additional_cases']
    output = ROOT / 'results/raw/hwp-guided-search'
    output.mkdir(parents=True, exist_ok=True)
    # Each run begins with an empty in-memory synthesis cache; reuse within the run is explicit.
    synth = RotationSynthesizer(seed=config['seed'])
    rows, timings = [], []
    for case in cases:
        started = time.perf_counter()
        library = build_library(load_program(case), config['total_error'], synth,
                                max_batch=config['max_batch'], max_terms=config['max_terms'])
        exact = frontier(library, config['ancilla_envelope'], timeout_seconds=config['frontier_seconds'])
        references = baseline_frontiers(library, config['ancilla_envelope'], timeout_seconds=config['baseline_seconds'])
        base = base_plans(library, config['ancilla_envelope'])
        if not exact.complete or not references['complete']:
            raise RuntimeError(f"incomplete diagnosis: {case['id']}")
        pool = pareto([*base, *(p for ps in references['frontiers'].values() for p in ps)])
        direct = best(references['frontiers']['direct'], (Fraction(1),)*3,
                      {'ancilla': config['ancilla_envelope'], 'depth': None})
        scales = (max(1, direct.resources[0]), max(1, direct.resources[1]), max(1, config['ancilla_envelope']))
        for limits in config['limits']:
            for pref in config['preferences'] + config['holdout_preferences']:
                weights = tuple(Fraction(x)/s for x,s in zip(pref, scales))
                p, b = best(exact.plans, weights, limits), best(pool, weights, limits)
                rows.append({'case': case['id'], 'limits': limits, 'preference': pref,
                             'scales': scales, 'weights': list(map(str, weights)),
                             'reference': b.resources if b else None, 'optimum': p.resources if p else None,
                             'reference_cost': str(cost(b.resources, weights)) if b else None,
                             'optimum_cost': str(cost(p.resources, weights)) if p else None,
                             'improvement': str(cost(b.resources, weights)-cost(p.resources, weights)) if b and p else None})
        timings.append({'case': case['id'], 'library': library.stats, 'frontier': exact.stats,
                        'reference_seconds': references['seconds'], 'total_seconds': time.perf_counter()-started})
        print(f"{case['id']}: diagnosis complete ({len(exact.plans)} model points)", flush=True)
    result = {'base_revision': config['base_revision'], 'config_sha256': sha(config_path),
              'original_source_fingerprint': previous['source_fingerprint'], 'source_mismatches': mismatches,
              'cache_policy': 'empty at process start, shared between cases', 'timings': timings, 'queries': rows}
    dump(ROOT / 'results/hwp-guided-diagnosis.json', result)
    lines = ['# Frozen cost diagnosis', '', 'Original study source hashes all match the implementation base. Costs are exact rationals; depth is complete-wave T-depth. Unrestricted means A <= 8. Both reference and model points are filtered by the same limits.', '',
             '| Input | Queries | Strict wins | Envelope wins | Example constrained T reference → model |', '|---|---:|---:|---:|---|']
    for case in cases:
        rs = [r for r in rows if r['case'] == case['id']]
        wins = [r for r in rs if r['improvement'] and Fraction(r['improvement']) > 0]
        ex = next(r for r in rs if r['limits']['id']=='constrained' and r['preference']==['1','0','0'])
        lines.append(f"| {case['id']} | {len(rs)} | {len(wins)} | {sum(r['limits']['id']=='envelope' for r in wins)} | {ex['reference']} → {ex['optimum']} |")
    lines += ['', 'The JSON gives the best reference, exact optimum, scales, effective coefficients, and improvement for every cost/limit query. This finite sweep makes no all-weights claim. The overlapping_6 witness (284,166,3) remains a constrained regression; the reference midpoint (270,134,2) dominates it geometrically but is not an executable circuit. H2 remains unestablished for unrestricted costs.', '']
    (ROOT / 'reports/hwp-guided-diagnosis.md').write_text('\n'.join(lines))


def repeat_call(count, call):
    values, seconds = [], []
    for _ in range(count):
        start = time.perf_counter()
        values.append(call())
        seconds.append(time.perf_counter()-start)
    return values[-1], seconds


def query_record(result):
    return {'status': result.status, 'reason': result.reason,
            'L': str(result.lower) if result.lower is not None else None,
            'U': str(result.upper) if result.upper is not None else None,
            'absolute_gap': str(result.absolute_gap) if result.absolute_gap is not None else None,
            'relative_gap': str(result.relative_gap) if result.relative_gap is not None else None,
            'fingerprint': result.fingerprint,
            'plan': result.plan.to_dict() if result.plan else None}


def evaluate(config, config_path):
    startup = time.perf_counter()-PROCESS_STARTED
    cases = yaml.safe_load((ROOT / config['development_config']).read_text())['cases'] + config['additional_cases']
    reps, envelope = config['repeats'], config['ancilla_envelope']
    frozen = json.loads((ROOT / 'results/hwp-guided-diagnosis.json').read_text())
    assert frozen['config_sha256'] == sha(config_path)
    source_paths = sorted((ROOT/'src/collective_phase').rglob('*.py')) + [Path(__file__), ROOT/'scripts/run_hwp_pareto.py', ROOT/'pyproject.toml']
    summary = {'config_sha256': sha(config_path), 'source_hashes': {str(p.relative_to(ROOT)):sha(p) for p in source_paths},
               'base_revision': config['base_revision'], 'revision_before_results': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               'versions': {p:importlib.metadata.version(p) for p in ['numpy','pyzx','pygridsynth','PyYAML']},
               'startup_seconds': startup, 'repeats': reps, 'cases': [], 'queries': [],
               'cache_policy': 'each case cold empty rotation cache, then three warm library builds; no cross-query search or verification cache',
               'timing_scope': 'query times include emission and verification; library times include template synthesis/verification; source fingerprint setup, seed and archive acquisition are separate charged costs; serialization excluded',
               'archive_policy': 'six development weights acquired separately per exact constraint fingerprint using reference seeds and structural bounds; only hold-out targets receive these certificates; same seed pool as structural ablation'}
    witness = None
    for case in cases:
        program = load_program(case)
        synth = RotationSynthesizer(seed=config['seed'])
        start = time.perf_counter()
        lib = build_library(program, config['total_error'], synth, max_batch=config['max_batch'], max_terms=config['max_terms'])
        cold_library = time.perf_counter()-start
        rotation_count = len(synth._cache)
        _, warm_library = repeat_call(reps, lambda: build_library(program, config['total_error'], synth, max_batch=config['max_batch'], max_terms=config['max_terms']))
        start = time.perf_counter()
        model = Model(lib)
        model_seconds = time.perf_counter()-start
        exact, exact_times = repeat_call(reps, lambda: frontier(lib, envelope, timeout_seconds=config['frontier_seconds']))
        direct, direct_times = repeat_call(reps, lambda: frontier(lib, envelope, timeout_seconds=config['frontier_seconds'], option_ids=frozenset(o.id for o in lib.options if o.layout=='direct')))
        def references():
            refs = baseline_frontiers(lib, envelope, timeout_seconds=config['baseline_seconds'])
            if not refs['complete']:
                raise RuntimeError('incomplete reference acquisition')
            return pareto([*base_plans(lib,envelope), *(p for ps in refs['frontiers'].values() for p in ps)])
        pool, pool_times = repeat_call(reps, references)
        assert exact.complete and direct.complete
        direct_plan = best(direct.plans, (Fraction(1),)*3, {'ancilla':envelope,'depth':None})
        scales = (max(1,direct_plan.resources[0]),max(1,direct_plan.resources[1]),max(1,envelope))
        records = []
        archive_times, archive_records, archives = {}, [], {}
        for limits in config['limits']:
            archive_start = time.perf_counter()
            certificates = []
            for pref in config['preferences']:
                w = tuple(Fraction(x)/s for x,s in zip(pref,scales))
                result = search(model,w,limits['ancilla'],limits['depth'],seeds=pool,
                                timeout_seconds=config['search_seconds'])
                certificates.append(CertifiedInequality.from_result(result))
                archive_records.append({'limits':limits['id'],'preference':pref,'weights':list(map(str,w)),
                                        **query_record(result),'stats':result.stats})
            archive_times[limits['id']] = time.perf_counter()-archive_start
            archives[limits['id']] = certificates
        for limits in config['limits']:
            for pref in config['preferences'] + config['holdout_preferences']:
                holdout = pref in config['holdout_preferences']
                w = tuple(Fraction(x)/s for x,s in zip(pref,scales))
                optimum = best(exact.plans,w,limits)
                reference = best(pool,w,limits)
                frozen_row = next(r for r in frozen['queries'] if r['case']==case['id'] and r['limits']==limits and r['preference']==pref)
                assert frozen_row['scales']==list(scales)
                assert frozen_row['optimum_cost']==(str(cost(optimum.resources,w)) if optimum else None)
                common = {'case':case['id'],'limits':limits['id'],'ancilla':limits['ancilla'],'depth':limits['depth'],
                          'preference':pref,'weights':list(map(str,w)),'scales':scales,'holdout_weight':holdout,
                          'optimum':str(cost(optimum.resources,w)) if optimum else None,
                          'reference':reference.resources if reference else None}
                # DP is computed once per sequence; each selected parent is verified like search incumbents.
                def select_verify():
                    p = best(exact.plans,w,limits)
                    if p is None:
                        return None,None,0.
                    start = time.perf_counter()
                    lowered,proof = emit(lib,p)
                    return estimate_resources(lowered).to_dict(),proof,time.perf_counter()-start
                dp, dp_times = repeat_call(reps,select_verify)
                records.append({**common,'method':'frontier','status':'OPTIMAL' if optimum else 'INFEASIBLE',
                                'L':common['optimum'],'U':common['optimum'],'absolute_gap':'0' if optimum else None,
                                'fingerprint':model.query_fingerprint(limits['ancilla'],limits['depth']),
                                'plan':optimum.to_dict() if optimum else None,'seconds':dp_times,
                                'median_seconds':statistics.median(dp_times),'verification_seconds':dp[2],
                                'emitted':dp[0],'states':0,'waves':0})
                for method in ['direct_trivial','reference_trivial','structural','archive']:
                    results=[]
                    for _ in range(reps):
                        result=search(model,w,limits['ancilla'],limits['depth'],
                                      seeds=direct.plans if method=='direct_trivial' else pool,
                                      structural=method in {'structural','archive'},
                                      certificates=archives[limits['id']] if method=='archive' and holdout else (),
                                      timeout_seconds=config['search_seconds'])
                        if optimum:
                            optimum_cost=cost(optimum.resources,w)
                            assert result.lower<=optimum_cost<=result.upper
                            if result.status=='OPTIMAL':
                                assert result.upper==optimum_cost
                        else:
                            assert result.plan is None
                        results.append(result)
                    result=results[-1]
                    records.append({**common,'method':method,**query_record(result),
                                    'seconds':[r.stats['seconds'] for r in results],
                                    'median_seconds':statistics.median(r.stats['seconds'] for r in results),
                                    'search_seconds':[r.stats['search_seconds'] for r in results],
                                    'verification_seconds':statistics.median(r.stats['verification_seconds'] for r in results),
                                    'states':result.stats['states'],'waves':result.stats['waves'],
                                    'emitted':result.stats.get('incumbent_emitted'),
                                    'gap_5_percent_seconds':[r.stats['gap_5_percent_seconds'] for r in results],
                                    'gap_1_percent_seconds':[r.stats['gap_1_percent_seconds'] for r in results],
                                    'first_improvement_seconds':[r.stats['first_improvement_seconds'] for r in results],
                                    'archive_lower':result.stats['archive_lower'],
                                    'pending_expansion_at_timeout':result.stats['pending_expansion_at_timeout']})
                    if case['id']=='overlapping_6' and limits['id']=='constrained' and pref==['1','0','0'] and method=='structural':
                        lowered,proof=emit(lib,result.plan)
                        witness={'case':case['id'],'query':common,**query_record(result),
                                 'program':program.to_dict(),'candidate':lowered.candidate.to_dict(),
                                 'lowering':lowered.to_dict(),'verification':proof,
                                 'resources':estimate_resources(lowered).to_dict()}
        timings={'case':case['id'],'library_cold_seconds':cold_library,'library_warm_seconds':warm_library,
                 'library':lib.stats,'rotations_synthesized':rotation_count,'model_setup_seconds':model_seconds,
                 'direct_seed_seconds':direct_times,'reference_seed_seconds':pool_times,
                 'frontier_seconds':exact_times,'frontier_stats':exact.stats,
                 'archive_seconds_by_limits':archive_times,'archive_sources':archive_records}
        summary['cases'].append(timings)
        summary['queries'].extend(records)
        print(f"{case['id']}: {len(records)} method/query records, all checked against exact optimum",flush=True)
        write_summary(summary)
    assert witness is not None
    dump(ROOT/'results/hwp-guided-witness.json',witness)
    (ROOT/'reports/hwp-guided-search.md').write_text(render_comparison(summary))
    print('Report: reports/hwp-guided-search.md',flush=True)


def write_summary(summary):
    # One JSON object per row keeps the tracked results compact and diffable.
    header={k:v for k,v in summary.items() if k not in {'cases','queries'}}
    text=json.dumps(header,indent=2)[:-2]+',\n  "cases": [\n'
    text+=',\n'.join(json.dumps(c,sort_keys=True) for c in summary['cases'])
    text+='\n  ],\n  "queries": [\n'+',\n'.join(json.dumps(r,sort_keys=True) for r in summary['queries'])+'\n  ]\n}\n'
    (ROOT/'results/hwp-guided-search.json').write_text(text)


def render_comparison(summary):
    rows=summary['queries']
    methods=['frontier','direct_trivial','reference_trivial','structural','archive']
    def acquisition(case,method):
        if method=='frontier':
            return statistics.median(case['frontier_seconds'])
        value=statistics.median(case['direct_seed_seconds'] if method=='direct_trivial' else case['reference_seed_seconds'])
        if method=='archive':
            value+=sum(case['archive_seconds_by_limits'].values())
        return value
    lines=['# Guided HWP search results','',
           f"{len(summary['cases'])} inputs × 27 queries × five methods × {summary['repeats']} timing repetitions. All optima and intervals were checked against the exact frontier. Preferences and extra inputs were frozen in the first commit. No construction was added.",
           '', '## Matched query sequence', '',
           'Times below sum per-query medians. Search/selection time includes incumbent emission and verification. Warm sequence totals charge one library build, model setup, and acquisition per input. The frontier is charged once across all 27 queries, not once per query. Archive acquisition includes six development queries for each of three exact limit fingerprints. Development targets use no archived certificates; only the nine hold-out queries per input receive them.', '',
           '| Method | Query seconds | Acquisition seconds | Warm sequence seconds | Expanded states | Generated waves |',
           '|---|---:|---:|---:|---:|---:|']
    for method in methods:
        rs=[r for r in rows if r['method']==method]
        query=sum(r['median_seconds'] for r in rs)
        acquired=sum(acquisition(c,method) for c in summary['cases'])
        common=sum(statistics.median(c['library_warm_seconds'])+c['model_setup_seconds'] for c in summary['cases'])
        states=sum(c['frontier_stats']['states'] for c in summary['cases']) if method=='frontier' else sum(r['states'] for r in rs)
        waves=sum(c['frontier_stats']['waves'] for c in summary['cases']) if method=='frontier' else sum(r['waves'] for r in rs)
        lines.append(f'| {method} | {query:.4f} | {acquired:.4f} | {common+acquired+query:.4f} | {states} | {waves} |')
    lines += ['', '## Cold and warm library costs', '',
              f"Measured process import/setup startup: {summary['startup_seconds']:.4f} s. Each cold library uses an empty synthesis cache; each warm figure is the median of three rebuilds with that case's rotation cache. A cold single query costs startup + cold library + model setup + its method acquisition + query time. A warm query with an already available library/archive costs the query time; the archive is never free in the sequence totals.", '',
              '| Input | Options / templates | New rotations | Cold library s | Warm library s | Frontier s | Reference acquisition s |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for c in summary['cases']:
        lines.append(f"| {c['case']} | {c['library']['options']} / {c['library']['templates']} | {c['rotations_synthesized']} | {c['library_cold_seconds']:.4f} | {statistics.median(c['library_warm_seconds']):.4f} | {statistics.median(c['frontier_seconds']):.4f} | {statistics.median(c['reference_seed_seconds']):.4f} |")
    lines += ['', '## Bound transfer on held-out weights', '',
              '| Input | Structural states | Archive states | Structural query s | Archive query s | Archive acquisition s |',
              '|---|---:|---:|---:|---:|---:|']
    for c in summary['cases']:
        rs=[r for r in rows if r['case']==c['case'] and r['holdout_weight']]
        structural=[r for r in rs if r['method']=='structural']
        archive=[r for r in rs if r['method']=='archive']
        lines.append(f"| {c['case']} | {sum(r['states'] for r in structural)} | {sum(r['states'] for r in archive)} | {sum(r['median_seconds'] for r in structural):.4f} | {sum(r['median_seconds'] for r in archive):.4f} | {sum(c['archive_seconds_by_limits'].values()):.4f} |")
    statuses={s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}
    lines += ['', '## Guarantees and evidence', '', f'Final method/query statuses: {statuses}.', '',
              'The machine-readable results include every preference and exact effective coefficient, limits, model fingerprint, reconstructed plan, measured emitted resources, U/L, absolute/relative gaps, three individual timings, states/waves, time to first improved incumbent, and times to 5%/1% certified gaps. Null threshold times mean the threshold was not reached; L=0 has no relative percentage. Options/templates and new rotations are reported separately. Library time includes template verification; query verification is also recorded separately.', '',
              'The tracked witness emits the constrained overlapping_6 circuit with modeled (T, wave D, A) = (284,166,3). Its JSON includes the original program, candidate, Clifford+T lowering, ordinary scheduled resources, verification evidence, and exact cost interval. The midpoint argument excludes using this witness as an unrestricted linear-cost win. The frozen baseline diagnosis found no unrestricted wins and two constrained cost wins among 351 queries; H2 remains unestablished.', '',
              'All five methods use identical templates, objective scales, legal waves and verification; seeds, structural bounds and archived inequalities are the intentionally varied components. The three search repetitions have the same 10-second deadline. Exact-frontier/reference acquisition retains its separately declared 120/180-second caps; all completed. No certificates come from the full frontier. Single-certificate transfer uses exact rational feasibility checks. No downstream optimizer was run, so there is no post-optimization guarantee.', '',
              'These tiny-case timings do not establish broad speedups. Compare work counts and charged totals, not isolated sub-millisecond differences. The complete library is synthesized up front in every method; this experiment cannot claim avoided subset synthesis. See the accompanying assessment in docs/hwp-guided-search.md for the stopping decision.', '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='configs/hwp-guided-search.yaml')
    parser.add_argument('--stage',choices=['diagnosis','evaluate'],default='evaluate')
    args=parser.parse_args()
    path=ROOT/args.config
    config=yaml.safe_load(path.read_text())
    (diagnosis if args.stage=='diagnosis' else evaluate)(config,path)


if __name__=='__main__':
    main()
