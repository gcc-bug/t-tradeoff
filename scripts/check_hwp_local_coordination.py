#!/usr/bin/env python3
"""A declared development witness for local/global resource coupling in real HWP."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from run_hwp_pareto import dump, load_program, sha
from run_hwp_interleaved_study import references
from collective_phase.hwp_cost_search import symbolic_search
from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.lowering import RotationSynthesizer

# Chosen to put two independently useful three-bit HWP blocks in competition
# for one clean carry. This is a mechanism witness, not a fresh holdout.
CASE = dict(id='local_coordination_3_3', kind='groups',
            groups=[dict(size=3, angle='0.173'), dict(size=3, angle='0.291')])
CONFIG = dict(total_error=1e-4, seed=0, max_batch=8, max_terms=10,
              orderings=['staged', 'readiness'], reference_seconds=30,
              queries=[dict(id='one_carry', weights=['1', '0', '0'], ancilla=1, depth=100)])


def main():
    reference = references(CASE, CONFIG)
    program = load_program(CASE)
    lib = SymbolicLibrary(program, CONFIG['total_error'], RotationSynthesizer(seed=0),
                          orderings=tuple(CONFIG['orderings']))
    result = symbolic_search(lib, (1, 0, 0), 1, 100, interleave=True, coupled_bounds=True,
                             timeout_seconds=30)
    evidence = dict(case=CASE, config=CONFIG, reference=reference,
                    status=result.status, lower=str(result.lower), upper=str(result.upper),
                    plan=None if result.plan is None else result.plan.to_dict(), stats=result.stats,
                    program=program.to_dict(), fingerprint=result.fingerprint,
                    source_hash=sha(Path(__file__)))
    if result.plan is not None:
        lowered, proof = lib.emit(result.plan, memory_cap_bytes=64*1024*1024)
        evidence.update(candidate=lowered.candidate.to_dict(), lowering=lowered.to_dict(), verification=proof,
                        options=[dict(id=i, terms=lib.options[i].terms, layout=lib.options[i].layout,
                                      ordering=lib.options[i].ordering)
                                 for wave in result.plan.waves for i in wave])
    dump(ROOT/'results/hwp-local-coordination.json.gz', evidence)
    row = reference['queries'][0]
    print('local group plans:', row['local_group_plans'])
    print('rescheduled local choices:', row['local'], 'complete:', row['local_complete'])
    print('full optimum:', row['full'], 'complete:', row['full_complete'])
    print('strong batching:', row['batching'], 'complete:', row['batching_complete'])
    print('interleaved:', result.status, evidence['plan'])
    print('verification:', evidence.get('verification'))


if __name__ == '__main__':
    main()
