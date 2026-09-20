#!/usr/bin/env python3
"""Frozen cost-query study, using the original library and circuit schemas."""
from __future__ import annotations
import argparse
from fractions import Fraction
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from run_hwp_pareto import load_program, base_plans, dump, sha
from collective_phase.hwp_pareto import build_library, frontier, baseline_frontiers, pareto
from collective_phase.lowering import RotationSynthesizer


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/hwp-guided-search.yaml')
    args = parser.parse_args()
    path = ROOT / args.config
    diagnosis(yaml.safe_load(path.read_text()), path)


if __name__ == '__main__':
    main()
