#!/usr/bin/env python3
"""Equal-budget development comparison; isolated caches, verified incumbents."""
from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from run_hwp_pareto import dump, load_program, sha
from run_hwp_symbolic_study import best, record, seed_plan
from collective_phase.hwp_cost_search import symbolic_search, cost, weights
from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.hwp_pareto import build_library, baseline_frontiers, frontier, emit, _Deadline
from collective_phase.lowering import RotationSynthesizer
from collective_phase.resources import estimate_resources


class BudgetSynthesizer(RotationSynthesizer):
    def __init__(self, seed, check):
        super().__init__(seed=seed)
        self.check = check

    def synthesize(self, *args, **kwargs):
        self.check()
        value = super().synthesize(*args, **kwargs)
        self.check()
        return value


def run_trial(case, config, method, budget, mode):
    started = time.perf_counter()
    deadline = started + budget
    def check():
        if time.perf_counter() >= deadline:
            raise _Deadline
    synth = BudgetSynthesizer(config['seed'], check)
    program = load_program(case)
    lib = None
    rows = []
    setup_seconds = 0.
    queries = config['queries'][:1] if mode == 'cold' else config['queries']
    for index, query in enumerate(queries):
        tick = started if index == 0 else time.perf_counter()
        deadline = tick + budget
        row = dict(status='TIMEOUT', reason='SETUP_TIMEOUT', L='0', U=None, gap=None, plan=None, stats={})
        try:
            if lib is None:
                setup_tick = time.perf_counter()
                kwargs = dict(max_batch=config['max_batch'], max_terms=config['max_terms'],
                              orderings=tuple(config['orderings']))
                if method == 'batching':
                    lib = build_library(program, config['total_error'], synth, check_time=check, **kwargs)
                else:
                    lib = SymbolicLibrary(program, config['total_error'], synth,
                                          evaluator='graph' if method == 'serial_graph' else 'transfer', **kwargs)
                setup_seconds += time.perf_counter() - setup_tick
            check()
            w = weights(query['weights'])
            if method != 'batching':
                result = symbolic_search(lib, w, query['ancilla'], query['depth'],
                    timeout_seconds=max(0., deadline-time.perf_counter()),
                    interleave=method.startswith('interleaved'),
                    coupled_bounds=method.endswith('coupled'),
                    resolve_upfront=method.startswith('upfront'))
                row = record(result)
            else:
                seed = seed_plan(lib)
                if seed.resources[2] <= query['ancilla'] and (query['depth'] is None or seed.resources[1] <= query['depth']):
                    check()
                    lowered, proof = emit(lib, seed)
                    value = cost(seed.resources, w)
                    row.update(status='FEASIBLE', U=str(value), gap=str(value), plan=seed.to_dict())
                    row['stats'].update(incumbent_verification=proof,
                                        incumbent_emitted=estimate_resources(lowered).to_dict())
                reference = baseline_frontiers(lib, query['ancilla'],
                                               timeout_seconds=max(0., deadline-time.perf_counter()))
                plan = best([p for ps in reference['frontiers'].values() for p in ps], w, query)
                row.update(reason='BATCHING', reference_complete=reference['complete'],
                           reference_seconds=reference['seconds'])
                row['stats']['partitions'] = reference['partitions']
                if plan is not None and (row['U'] is None or cost(plan.resources, w) < Fraction(row['U'])):
                    # Reserve no unreported verification time: if the search
                    # consumed the budget, its unverified plan is not an incumbent.
                    check()
                    lowered, proof = emit(lib, plan)
                    value = cost(plan.resources, w)
                    row.update(status='FEASIBLE', U=str(value), gap=str(value), plan=plan.to_dict())
                    row['stats'].update(incumbent_verification=proof,
                                        incumbent_emitted=estimate_resources(lowered).to_dict())
                elif plan is None and reference['complete']:
                    # This is infeasibility only within the batching subset.
                    row['reason'] = 'BATCHING_INFEASIBLE'
        except _Deadline:
            pass
        elapsed = time.perf_counter()-tick
        row.update(query=query['id'], weights=query['weights'], seconds=elapsed,
                   overrun_seconds=max(0., elapsed-budget), setup_seconds=setup_seconds if index == 0 else 0.)
        rows.append(row)
    return dict(method=method, mode=mode, budget=budget, case=case['id'],
                seconds=time.perf_counter()-started, queries=rows,
                library_stats={} if lib is None else dict(lib.stats))


def references(case, config):
    started = time.perf_counter()
    program = load_program(case)
    lib = build_library(program, config['total_error'], RotationSynthesizer(seed=config['seed']),
                        max_batch=config['max_batch'], max_terms=config['max_terms'],
                        orderings=tuple(config['orderings']))
    rows = []
    for query in config['queries']:
        w = weights(query['weights'])
        exact = frontier(lib, query['ancilla'], query['depth'], timeout_seconds=config['reference_seconds'])
        batching = baseline_frontiers(lib, query['ancilla'], timeout_seconds=config['reference_seconds'])
        full_best = best(exact.plans, w, query)
        batch_best = best([p for ps in batching['frontiers'].values() for p in ps], w, query)
        # Deliberately retain one independently optimal plan for each angle group.
        # Scheduling those selected blocks globally cannot recover discarded choices.
        selected, local_complete = set(), True
        local_details = []
        for group in lib.groups:
            mask = sum(1 << i for i in group)
            sub = SimpleNamespace(terms=lib.terms, full_mask=mask,
                                  options=[o for o in lib.options if o.terms & mask == o.terms])
            result = frontier(sub, query['ancilla'], timeout_seconds=config['reference_seconds'])
            local_complete &= result.complete
            p = min(result.plans, key=lambda p: (cost(p.resources, w), p.resources, p.waves), default=None)
            if p is not None:
                selected.update(i for wave in p.waves for i in wave)
                local_details.append(p.to_dict())
        restricted = frontier(lib, query['ancilla'], query['depth'], option_ids=selected,
                              timeout_seconds=config['reference_seconds'])
        local_best = best(restricted.plans, w, query)
        verified = {}
        for name, p in [('full', full_best), ('batching', batch_best), ('local', local_best)]:
            if p is not None:
                _, proof = emit(lib, p)
                verified[name] = proof
        rows.append(dict(query=query['id'], full_complete=exact.complete,
                         batching_complete=batching['complete'], local_complete=local_complete and restricted.complete,
                         full=None if full_best is None else full_best.to_dict(),
                         batching=None if batch_best is None else batch_best.to_dict(),
                         local=None if local_best is None else local_best.to_dict(),
                         local_group_plans=local_details, verification=verified))
    return dict(case=case['id'], seconds=time.perf_counter()-started, queries=rows)


def validate(samples, refs):
    known = {(r['case'], q['query']): q for r in refs for q in r['queries']}
    groups = defaultdict(list)
    for sample in samples:
        for row in sample['queries']:
            groups[sample['case'], row['query']].append(row)
    for key, rows in groups.items():
        ref = known[key]
        optima = {Fraction(r['U']) for r in rows if r['status'] == 'OPTIMAL'}
        w = weights(rows[0]['weights'])
        if ref['full_complete'] and ref['full'] is not None:
            optima.add(cost(ref['full']['resources'], w))
        assert len(optima) <= 1, (key, optima)
        if optima:
            optimum = next(iter(optima))
            for row in rows:
                assert row['status'] != 'INFEASIBLE', key
                assert row['L'] is None or Fraction(row['L']) <= optimum, key
                assert row['U'] is None or Fraction(row['U']) >= optimum, key
        elif ref['full_complete']:
            assert all(row['U'] is None for row in rows), key
        for row in rows:
            if row['U'] is not None:
                assert row['stats']['incumbent_verification']['status'].startswith('verified_lowered_'), key


def report(data, path):
    samples, refs = data['samples'], data['references']
    lines = ['# Interleaved HWP development comparison', '',
             'Same staged/readiness constructions, precision policy and complete-wave model. '
             'Each query pays its declared wall-clock budget; the first pays input loading and setup. '
             'Cold runs the first query; warm runs both with caches shared only inside that trial. '
             'All incumbents are emitted and verified. These are development inputs, not holdouts.', '',
             '| Mode | Budget/query s | Method | Certified optimum / queries | Verified incumbent / queries | Median trial s |',
             '|---|---:|---|---:|---:|---:|']
    config = data['config']
    for mode in config['modes']:
        for budget in config['budgets_seconds']:
            for method in config['methods']:
                selected = [s for s in samples if (s['mode'], s['budget'], s['method']) == (mode, budget, method)]
                rows = [r for s in selected for r in s['queries']]
                if rows:
                    lines.append(f"| {mode} | {budget} | {method} | {sum(r['status']=='OPTIMAL' for r in rows)} / {len(rows)} | "
                                 f"{sum(r['U'] is not None for r in rows)} / {len(rows)} | {statistics.median(s['seconds'] for s in selected):.4f} |")
    lines += ['', 'Batching is a restricted reference family: its completion does not certify the full-family optimum. '
              'Missing verified incumbents include exhausted budgets during setup or before final verification. '
              'Mixed completion counts are not equal-quality speedups.', '',
              '| Fixed-budget pair: interleaved_coupled vs upfront_coupled | Better U | Equal U | Worse U | Only interleaved feasible | Only upfront feasible | Neither feasible |',
              '|---|---:|---:|---:|---:|---:|---:|']
    indexed = {(s['case'], s['mode'], s['budget'], s['repeat'], s['method']): s for s in samples}
    for mode in config['modes']:
        for budget in config['budgets_seconds']:
            counts = [0]*6
            for sample in samples:
                if (sample['mode'], sample['budget'], sample['method']) != (mode, budget, 'interleaved_coupled'):
                    continue
                other = indexed[sample['case'], mode, budget, sample['repeat'], 'upfront_coupled']
                for a, b in zip(sample['queries'], other['queries']):
                    u, v = a['U'], b['U']
                    i = (5 if u is None and v is None else 4 if u is None else 3 if v is None else
                         0 if Fraction(u)<Fraction(v) else 2 if Fraction(u)>Fraction(v) else 1)
                    counts[i] += 1
            lines.append(f"| {mode}, {budget}s | " + ' | '.join(map(str, counts)) + ' |')
    lines += ['', '| Separate reference | Query | Full-family best (complete?) | Strong batching best (complete?) | One local optimum/group (complete?) |',
              '|---|---|---|---|---|']
    for ref in refs:
        for row in ref['queries']:
            cells = []
            for name in ('full', 'batching', 'local'):
                point = None if row[name] is None else tuple(row[name]['resources'])
                cells.append(f"{point} ({row[name+'_complete']})")
            lines.append(f"| {ref['case']} | {row['query']} | " + ' | '.join(cells) + ' |')
    overruns = [r['overrun_seconds'] for s in samples for r in s['queries']]
    lines += ['', f"Maximum measured deadline overrun: {max(overruns, default=0):.4f}s. "
              'Atomic synthesis/verification and descriptor initialization can overrun and are charged.', '',
              'Raw records include L/U, plans, fingerprints, first incumbent/improvement, graph and recipe counts, '
              'evaluations, refinements, queue sizes, partial waves, setup time and actual elapsed time. '
              'Separate longer references and local-choice diagnostics are never supplied to timed searches.', '',
              'This experiment changes evaluation and search, not the arithmetic family. Any fixed-budget quality advantage '
              'is controller performance; any completed full-family result shared with batching is not a new circuit-family gain. '
              'No published-method superiority or within-block release/reuse claim follows.', '']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/hwp-interleaved-study.yaml')
    parser.add_argument('--output', default='results/hwp-interleaved-study.json.gz')
    parser.add_argument('--report', default='reports/hwp-interleaved-study.md')
    args = parser.parse_args()
    config = yaml.safe_load((ROOT/args.config).read_text())
    source_paths = [*sorted((ROOT/'src/collective_phase').rglob('*.py')), Path(__file__), ROOT/args.config,
                    ROOT/'scripts/run_hwp_symbolic_study.py', ROOT/'scripts/run_hwp_pareto.py']
    data = dict(config=config, hashes={str(p.relative_to(ROOT)): sha(p) for p in source_paths}, samples=[], references=[])
    output = ROOT/args.output
    for case in config['cases']:
        for budget in config['budgets_seconds']:
            for mode in config['modes']:
                for repeat in range(config['repeats']):
                    methods = config['methods']
                    methods = methods[repeat % len(methods):] + methods[:repeat % len(methods)]
                    for method in methods:
                        trial = run_trial(case, config, method, budget, mode)
                        trial['repeat'] = repeat
                        data['samples'].append(trial)
                    print(case['id'], budget, mode, repeat, 'done', flush=True)
                    dump(output, data)
    # Run after timing to prevent reference cache effects in the first trial.
    for case in config['cases']:
        data['references'].append(references(case, config))
        dump(output, data)
        print(case['id'], 'references done', flush=True)
    validate(data['samples'], data['references'])
    data['validation'] = 'all comparable intervals and verified incumbents checked'
    dump(output, data)
    report(data, ROOT/args.report)


if __name__ == '__main__':
    main()
