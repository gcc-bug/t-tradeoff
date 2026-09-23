#!/usr/bin/env python3
"""Replay saved plans and inspect independent local choices after the timed study."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import platform
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from run_hwp_pareto import load_program, dump, sha
from run_hwp_nine_study import validate
from collective_phase.hwp_pareto import Plan, build_library, frontier, emit
from collective_phase.lowering import RotationSynthesizer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='results/hwp-nine-study.json.gz')
    parser.add_argument('--output', default='results/hwp-nine-validation.json.gz')
    args = parser.parse_args()
    source = ROOT/args.input
    with gzip.open(source, 'rt') as stream:
        data = json.load(stream)
    for path, expected in data['hashes'].items():
        assert sha(ROOT/path) == expected, f'stale study source: {path}'
    validate(data['samples']+data['coupled_samples'], data['references'])
    cfg = data['config']
    output = dict(study_hash=sha(source), checker_hash=sha(Path(__file__)),
                  environment=dict(python=platform.python_version(), machine=platform.machine()),
                  replays=[], local_diagnostics=[], dense_witnesses=[])
    cases = [cfg['case'], *cfg['coupled_cases']]
    for case in cases:
        lib = build_library(load_program(case), cfg['total_error'], RotationSynthesizer(seed=cfg['seed']),
                            max_batch=cfg['max_batch'], orderings=tuple(cfg['orderings']))
        seen = set()
        for sample in data['samples']+data['coupled_samples']:
            if sample['case'] != case['id']:
                continue
            for row in sample['queries']:
                if row['plan'] is None:
                    continue
                p = row['plan']
                plan = Plan(tuple(p['resources']), tuple(tuple(w) for w in p['waves']))
                if plan in seen:
                    continue
                seen.add(plan)
                _, proof = emit(lib, plan)
                output['replays'].append(dict(case=case['id'], plan=plan.to_dict(), proof=proof))
        if case == cfg['case']:
            continue
        refs = [r for r in data['references'] if r['case'] == case['id']]
        for ancilla in cfg['coupled_ancillas']:
            selected, local = set(), []
            for group in lib.groups:
                mask = sum(1 << i for i in group)
                sub = SimpleNamespace(terms=lib.terms, full_mask=mask,
                    options=[o for o in lib.options if o.terms & mask == o.terms])
                result = frontier(sub, ancilla, timeout_seconds=cfg['reference_seconds'])
                assert result.complete
                p = min(result.plans, key=lambda p: p.resources)
                selected.update(i for w in p.waves for i in w)
                local.append(p.to_dict())
            for depth in cfg['coupled_depths']:
                restricted = frontier(lib, ancilla, depth, option_ids=selected,
                                      timeout_seconds=cfg['reference_seconds'])
                assert restricted.complete
                full = next(r for r in refs if r['ancilla'] == ancilla and r['depth'] == depth)
                best = min(full['partition_frontier'], key=lambda p: tuple(p['resources']), default=None)
                chosen = min(restricted.plans, key=lambda p: p.resources, default=None)
                output['local_diagnostics'].append(dict(case=case['id'], ancilla=ancilla, depth=depth,
                    local=local, rescheduled=None if chosen is None else chosen.to_dict(), global_best=best))
                if ancilla == 1 and depth == 100 and best is not None:
                    p = Plan(tuple(best['resources']), tuple(tuple(w) for w in best['waves']))
                    lowered, proof = emit(lib, p, memory_cap_bytes=64*1024*1024)
                    assert proof['status'] == 'verified_lowered_dense'
                    output['dense_witnesses'].append(dict(case=case['id'], plan=p.to_dict(), proof=proof,
                        candidate=lowered.candidate.to_dict(), lowering=lowered.to_dict()))
    dump(ROOT/args.output, output)
    print(f"Replayed {len(output['replays'])} distinct saved plans; checked {len(output['local_diagnostics'])} local/global queries.")
    for witness in output['dense_witnesses']:
        print(witness['case'], witness['plan']['resources'], witness['proof']['operator_norm_error'])


if __name__ == '__main__':
    main()
