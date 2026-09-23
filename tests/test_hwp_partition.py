from itertools import product

import pytest

from collective_phase.hwp_partition import partition_frontier
from collective_phase.hwp_pareto import build_library, emit, _Deadline
from collective_phase.ir import AngleBinding, PhaseProgram, PhaseBlock, ParityTerm, make_program
from collective_phase.lowering import RotationSynthesizer
from test_hwp_cost_search import enumerate_resources


def nondominated(resources):
    return {r for r in resources if not any(s != r and all(x <= y for x, y in zip(s, r))
                                            for s in resources)}


def test_native_partition_frontier_against_independent_exhaustive_schedules():
    programs = [make_program('native', 4, [1, 2, 4, 8], AngleBinding('a', '0.173')),
                PhaseProgram('groups', 4, (AngleBinding('a', '0.173'), AngleBinding('b', '0.291')),
                    (PhaseBlock('block', tuple(ParityTerm(str(i), 1 << i, 'a' if i < 2 else 'b')
                                               for i in range(4))),)),
                PhaseProgram('boundaries', 2, (AngleBinding('a', 'pi/4'),),
                    (PhaseBlock('b0', (ParityTerm('0', 1, 'a'),)),
                     PhaseBlock('b1', (ParityTerm('1', 2, 'a'),))))]
    synth = RotationSynthesizer(seed=0)
    for program in programs:
        lib = build_library(program, 1e-4, synth, orderings=('staged', 'readiness'))
        for cap, depth in product((0, 1, 2, 4), (None, 0, 100)):
            oracle = {r for r in enumerate_resources(lib, lib.full_mask, cap)
                      if depth is None or r[1] <= depth}
            result = partition_frontier(lib, cap, depth)
            assert result.complete
            assert {p.resources for p in result.plans} == nondominated(oracle)
            for plan in result.plans:
                _, proof = emit(lib, plan)
                assert proof['status'].startswith('verified_lowered_')


def test_partition_domain_and_interruption():
    synth = RotationSynthesizer(seed=0)
    overlap = build_library(make_program('overlap', 3, [3, 5, 6], AngleBinding('a', '0.173')), 1e-4, synth)
    with pytest.raises(ValueError, match='disjoint singleton'):
        partition_frontier(overlap, 4)
    native = build_library(make_program('native', 3, [1, 2, 4], AngleBinding('a', '0.173')), 1e-4, synth)
    result = partition_frontier(native, 4, timeout_seconds=0)
    assert not result.complete and not result.plans
    def stop(plan):
        raise _Deadline
    result = partition_frontier(native, 4, on_plan=stop)
    assert not result.complete and not result.plans
    # Dropping just one subset breaks exchangeability; never silently certify.
    native.options = tuple(o for o in native.options if o.terms != 1)
    with pytest.raises(ValueError, match='nonexchangeable'):
        partition_frontier(native, 4)
