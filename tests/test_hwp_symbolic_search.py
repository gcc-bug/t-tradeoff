from fractions import Fraction
from itertools import product
from types import SimpleNamespace

import pytest

from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.hwp_cost_search import symbolic_search, completion_bounds, cost, weights
from collective_phase.hwp_pareto import build_library, _Deadline
from collective_phase.ir import AngleBinding, ParityTerm, PhaseBlock, PhaseProgram, make_program
from collective_phase.lowering import RotationSynthesizer
from test_hwp_cost_search import enumerate_resources, TickClock


@pytest.fixture(scope='module')
def cases():
    a = AngleBinding('a','0.173')
    programs = [make_program('native',3,[1,2,4],a), make_program('overlap',3,[3,5,6],a),
        PhaseProgram('boundaries',2,(AngleBinding('a','pi/4'),),(
            PhaseBlock('b',(ParityTerm('x',1,'a'),)), PhaseBlock('c',(ParityTerm('y',2,'a'),))))]
    synth = RotationSynthesizer()
    return [(p, synth, build_library(p,1e-4,synth,orderings=('staged','readiness'))) for p in programs]


def test_every_partial_bound_and_refinement_order(cases):
    for program, synth, eager in cases:
        for reverse in (False,True):
            lib = SymbolicLibrary(program,1e-4,synth,orderings=('staged','readiness'))
            requests = list({r.key:r for o in lib.options for r in lib.unresolved(o)}.values())
            if reverse:
                requests.reverse()
            for step in range(len(requests)+1):
                for cap in (0,2,4):
                    views = [SimpleNamespace(terms=o.terms, resources=lib.evaluate(o).lower)
                             for o in lib.options if o.workspace <= cap]
                    for remaining in range(lib.full_mask+1):
                        bound = completion_bounds(lib,remaining,views)
                        for actual in enumerate_resources(eager,remaining,cap):
                            assert all(x <= y for x,y in zip(bound,actual))
                if step < len(requests):
                    lib.refine(requests[step])


def test_exact_optima_against_independent_partition_wave_oracle(cases):
    for program, synth, eager in cases:
        for cap in (0,2,4):
            oracle = enumerate_resources(eager,eager.full_mask,cap)
            for pref, depth, pruning in product([(1,0,0),(0,1,0),('1/3','1/3','1/3'),(0,0,1)],
                                                [None,100,0], [False,True]):
                lib = SymbolicLibrary(program,1e-4,synth,orderings=('staged','readiness'))
                w = weights(pref)
                optimum = min((cost(r,w) for r in oracle if depth is None or r[1]<=depth),default=None)
                result = symbolic_search(lib,w,cap,depth,partial_pruning=pruning)
                if optimum is None:
                    assert result.status == 'INFEASIBLE'
                else:
                    assert result.status == 'OPTIMAL'
                    assert result.lower == result.upper == optimum
                    assert result.stats['incumbent_verification']['status'].startswith('verified_lowered_')


@pytest.mark.parametrize('stage', ['start','refinement','partial_wave','partial_wave_scan','before_emission','materialization'])
def test_interruption_retains_every_pending_family(cases, stage):
    program, synth, eager = cases[0]
    optimum = min(r[0] for r in enumerate_resources(eager,eager.full_mask,4))
    hit = False
    for occurrence in (1,2,5,12):
        lib = SymbolicLibrary(program,1e-4,synth,orderings=('staged','readiness'))
        count = 0
        def stop(where):
            nonlocal count, hit
            if where == stage:
                count += 1
                if count == occurrence:
                    hit = True
                    raise _Deadline
        result = symbolic_search(lib,(1,0,0),4,checkpoint=stop)
        assert result.lower <= optimum
        assert result.upper is None or result.upper >= optimum
        if result.reason == 'TIMEOUT':
            assert result.status in {'TIMEOUT','FEASIBLE','OPTIMAL'}
            assert result.stats['pending_expansion_at_timeout']
        if result.upper is not None:
            assert result.stats['incumbent_verification']['status'].startswith('verified_lowered_')
    assert hit


def test_zero_deadline_empty_input_and_failure(cases, monkeypatch):
    program, synth, eager = cases[0]
    lib = SymbolicLibrary(program,1e-4,synth)
    result = symbolic_search(lib,(1,0,0),4,timeout_seconds=0)
    assert result.status=='TIMEOUT' and result.lower==0 and result.upper is None
    def broken(*args, **kwargs):
        raise ValueError('verification failure')
    monkeypatch.setattr(lib,'emit',broken)
    with pytest.raises(ValueError,match='verification failure'):
        symbolic_search(lib,(1,0,0),4)
    zero = make_program('empty',1,[1,1],AngleBinding('a','0.173'),coefficients=[1,-1])
    empty = symbolic_search(SymbolicLibrary(zero,1e-4,synth),(1,0,0),0)
    assert empty.status=='OPTIMAL' and empty.plan.resources==(0,0,0)
    for timeout in (0.01,0.03,0.06):
        result = symbolic_search(SymbolicLibrary(program,1e-4,synth),(1,0,0),4,
                                 timeout_seconds=timeout,clock=TickClock())
        optimum = min(r[0] for r in enumerate_resources(eager,eager.full_mask,4))
        assert result.lower <= optimum
        assert result.upper is None or optimum <= result.upper


def test_workspace_filter_before_graphs_and_selective_materialization():
    program = make_program('native',8,[1<<i for i in range(8)],AngleBinding('a','0.173'))
    lib = SymbolicLibrary(program,1e-4,RotationSynthesizer())
    result = symbolic_search(lib,(1,0,0),0)
    assert result.status=='OPTIMAL'
    assert lib.stats['graphs']==lib.stats['templates_materialized']==1
    assert lib.stats['rotations_refined']==1
    assert lib.stats['circuits_verified']==1


def test_original_constrained_witness():
    program = make_program('overlapping_6',3,[1,2,3,4,5,6],AngleBinding('a','0.173'))
    lib = SymbolicLibrary(program,1e-4,RotationSynthesizer(),max_batch=8)
    result = symbolic_search(lib,(1,0,0),3,200)
    assert result.status=='OPTIMAL' and result.plan.resources==(284,166,3)
    midpoint = tuple(Fraction(x+y,2) for x,y in zip((228,112,4),(312,156,0)))
    assert all(x<y for x,y in zip(midpoint,result.plan.resources))


def test_depth_failure_of_direct_seed_does_not_mean_infeasible(cases):
    program, synth, _ = cases[1]
    # All three predicates overlap, so the direct seed is serial and too deep.
    lib = SymbolicLibrary(program,1e-4,synth)
    result = symbolic_search(lib,(1,0,0),4,100)
    assert result.status=='OPTIMAL'
    assert result.plan.resources[1] <= 100
    assert any(lib.options[i].layout=='copied_parities' for w in result.plan.waves for i in w)


def test_refinement_interrupt_after_backend_keeps_checked_shared_result(cases):
    program, synth, _ = cases[0]
    lib = SymbolicLibrary(program,1e-4,synth)
    request = lib.options[0].requests[0]
    calls = 0
    def after_backend():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise _Deadline
    with pytest.raises(_Deadline):
        lib.refine(request,after_backend)
    assert request.key in lib.rotations and lib.epoch==1
    before = lib.stats['rotations_refined']
    for o in lib.options:
        if o.layout=='direct':
            lib.resolve(o)
    assert lib.stats['rotations_refined']==before


def test_expanded_family_is_available_to_strong_batching_reference():
    from collective_phase.hwp_pareto import baseline_frontiers
    program = make_program('native',6,[1<<i for i in range(6)],AngleBinding('a','0.173'))
    eager = build_library(program,1e-4,RotationSynthesizer(),orderings=('staged','readiness'))
    refs = baseline_frontiers(eager,4,timeout_seconds=30)
    assert refs['complete']
    for name in ('uniform','per_group'):
        assert (204,68,4) in {p.resources for p in refs['frontiers'][name]}
