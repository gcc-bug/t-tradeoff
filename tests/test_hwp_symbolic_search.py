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


@pytest.mark.parametrize('coupled', [False, True])
@pytest.mark.parametrize('upfront', [False, True])
def test_interleaved_exact_optima(cases, coupled, upfront):
    for program, synth, eager in cases:
        for cap in (0, 2, 4):
            oracle = enumerate_resources(eager, eager.full_mask, cap)
            for pref, depth in product([(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)], [None, 100, 0]):
                lib = SymbolicLibrary(program, 1e-4, synth, orderings=('staged', 'readiness'))
                w = weights(pref)
                optimum = min((cost(r, w) for r in oracle if depth is None or r[1] <= depth), default=None)
                result = symbolic_search(lib, w, cap, depth, interleave=True,
                                         coupled_bounds=coupled, resolve_upfront=upfront)
                if optimum is None:
                    assert result.status == 'INFEASIBLE'
                else:
                    assert result.status == 'OPTIMAL'
                    assert result.lower == result.upper == optimum
                    assert result.stats['incumbent_verification']['status'].startswith('verified_lowered_')


def test_coupled_bounds_at_every_remaining_state_and_refinement(cases):
    from collective_phase.hwp_cost_search import coupled_completion_bounds
    for program, synth, eager in cases:
        lib = SymbolicLibrary(program, 1e-4, synth, orderings=('staged', 'readiness'))
        requests = list({r.key: r for o in lib.options for r in lib.unresolved(o)}.values())
        for request in [None, *reversed(requests)]:
            if request is not None:
                lib.refine(request)
            for cap in (0, 2, 4):
                views = [SimpleNamespace(terms=o.terms, boundary=o.boundary, footprint=o.footprint,
                                         resources=lib.evaluate(o).lower)
                         for o in lib.options if o.workspace <= cap]
                for remaining in range(lib.full_mask + 1):
                    bound = coupled_completion_bounds(lib, remaining, views, cap)
                    original = completion_bounds(lib, remaining, views)
                    assert all(a <= b for a, b in zip(original, bound))
                    for actual in enumerate_resources(eager, remaining, cap):
                        assert all(a <= b for a, b in zip(bound, actual))


@pytest.mark.parametrize('stage', ['bound_scan', 'partial_wave', 'partial_wave_scan',
                                   'wave_close', 'refinement', 'before_emission', 'materialization'])
def test_interleaved_interruptions_keep_open_and_sibling_families(cases, stage):
    program, synth, eager = cases[0]
    optimum = min(r[0] for r in enumerate_resources(eager, eager.full_mask, 4))
    hit = False
    for occurrence in (1, 2, 5, 12, 24):
        lib = SymbolicLibrary(program, 1e-4, synth, orderings=('staged', 'readiness'))
        count = 0
        def stop(where):
            nonlocal count, hit
            if where == stage:
                count += 1
                if count == occurrence:
                    hit = True
                    raise _Deadline
        result = symbolic_search(lib, (1, 0, 0), 4, interleave=True, coupled_bounds=True, checkpoint=stop)
        assert result.lower <= optimum
        assert result.upper is None or optimum <= result.upper
        if result.reason == 'TIMEOUT':
            assert result.stats['pending_expansion_at_timeout']
    assert hit


def test_refinement_arrives_before_first_wave_closes(cases):
    program, synth, _ = cases[0]
    lib = SymbolicLibrary(program, 1e-4, synth, orderings=('staged', 'readiness'))
    def stop(stage):
        if stage == 'wave_close':
            raise _Deadline
    result = symbolic_search(lib, (1, 0, 0), 4, interleave=True, checkpoint=stop)
    assert result.reason == 'TIMEOUT'
    assert result.stats['waves'] == 0
    assert result.stats['interleaved_refinements'] > 0


def test_target_query_returns_verified_plan_or_normal_certificate(cases):
    program, synth, eager = cases[0]
    optimum = min(r[0] for r in enumerate_resources(eager, eager.full_mask, 4))
    for target in (0, optimum, optimum + 1000):
        lib = SymbolicLibrary(program, 1e-4, synth)
        result = symbolic_search(lib, (1, 0, 0), 4, target_cost=target, interleave=True)
        assert result.lower <= optimum <= result.upper
        assert result.stats['target_reached'] == (result.upper <= target)
        if not result.stats['target_reached']:
            assert result.status == 'OPTIMAL'
        assert result.stats['incumbent_verification']['status'].startswith('verified_lowered_')
    with pytest.raises(ValueError, match='target'):
        symbolic_search(lib, (1, 0, 0), 4, target_cost=-1)


def test_local_depth_optima_lose_to_global_workspace_tradeoff():
    """Abstract scheduling witness, not a claim about physical HWP resources."""
    from collective_phase.hwp_pareto import frontier
    from collective_phase.hwp_cost_search import coupled_completion_bounds
    options = tuple(SimpleNamespace(id=i, terms=1 << (i // 2), footprint=1 << (i // 2),
                                    boundary=0, resources=(20, 10, 4) if i % 2 == 0 else (20, 12, 2))
                    for i in range(4))
    lib = SimpleNamespace(options=options, terms=(None, None), full_mask=3)
    local = frontier(lib, 4, option_ids={0, 2})
    global_result = frontier(lib, 4)
    assert min(p.resources[1] for p in local.plans) == 20
    best = min(global_result.plans, key=lambda p: p.resources[1])
    assert best.resources == (40, 12, 4)
    assert best.waves == ((1, 3),)
    bound = coupled_completion_bounds(lib, 3, options, 4)
    assert all(x <= y for x, y in zip(bound, best.resources))
    # Workspace volume alone forces D >= (4*10 + 4*10)/4 = 20.
    assert coupled_completion_bounds(lib, 3, options[::2], 4)[1] == 20


def test_coupled_bound_accounts_for_wire_conflicts_and_boundaries():
    from collective_phase.hwp_cost_search import coupled_completion_bounds
    # Each pair of terms must serialize on its common data wire. The two
    # different original boundaries must also serialize even on disjoint wires.
    options = [SimpleNamespace(terms=1 << i, footprint=1 << (i // 2), boundary=i // 2,
                               resources=(10, 7, 0)) for i in range(4)]
    lib = SimpleNamespace(terms=(None,)*4)
    assert completion_bounds(lib, 15, options) == (40, 7, 0)
    assert coupled_completion_bounds(lib, 15, options, 0) == (40, 28, 0)


def test_interleaved_without_partial_pruning(cases):
    program, synth, eager = cases[1]
    optimum = min(r[0] for r in enumerate_resources(eager, eager.full_mask, 4) if r[1] <= 100)
    result = symbolic_search(SymbolicLibrary(program, 1e-4, synth), (1, 0, 0), 4, 100,
                             interleave=True, partial_pruning=False, coupled_bounds=True)
    assert result.lower == result.upper == optimum


def test_real_hwp_local_optima_can_fail_a_global_depth_cap():
    from collective_phase.hwp_pareto import frontier
    a, b = AngleBinding('a0', '0.173'), AngleBinding('a1', '0.291')
    program = PhaseProgram('local-coordination', 6, (a, b), (PhaseBlock('block', tuple(
        ParityTerm(f't{i}', 1 << i, 'a0' if i < 3 else 'a1') for i in range(6))),))
    synth = RotationSynthesizer(seed=0)
    eager = build_library(program, 1e-4, synth, orderings=('staged', 'readiness'))
    selected, local = set(), []
    for group in eager.groups:
        mask = sum(1 << i for i in group)
        sub = SimpleNamespace(terms=eager.terms, full_mask=mask,
                              options=[o for o in eager.options if o.terms & mask == o.terms])
        result = frontier(sub, 1)
        assert result.complete
        p = min(result.plans, key=lambda p: p.resources)
        local.append(p)
        selected.update(i for wave in p.waves for i in wave)
    assert {p.resources for p in local} == {(114, 56, 1), (110, 54, 1)}
    restricted = frontier(eager, 1, 100, option_ids=selected)
    assert restricted.complete and not restricted.plans
    lib = SymbolicLibrary(program, 1e-4, synth, orderings=('staged', 'readiness'))
    result = symbolic_search(lib, (1, 0, 0), 1, 100, interleave=True, coupled_bounds=True)
    assert result.status == 'OPTIMAL' and result.plan.resources == (258, 56, 1)
    assert result.stats['incumbent_verification']['status'].startswith('verified_lowered_')


def test_native_nine_count_certificate_against_partition_only_oracle():
    # With no depth cap, any partition of individually feasible blocks can run
    # serially. Independent subset DP therefore gives the exact minimum T cost
    # without relying on either production wave enumerator.
    from functools import lru_cache
    program = make_program('native-nine', 9, [1 << i for i in range(9)], AngleBinding('a', '0.173'))
    synth = RotationSynthesizer(seed=0)
    eager = build_library(program, 1e-4, synth, max_batch=8, orderings=('staged', 'readiness'))
    @lru_cache(None)
    def partition_cost(remaining):
        if not remaining:
            return 0
        anchor = remaining & -remaining
        return min(o.resources[0] + partition_cost(remaining ^ o.terms)
                   for o in eager.options if o.resources[2] <= 4 and o.terms & anchor
                   and o.terms & remaining == o.terms)
    optimum = partition_cost(eager.full_mask)
    assert optimum == 310
    lib = SymbolicLibrary(program, 1e-4, synth, max_batch=8, orderings=('staged', 'readiness'))
    result = symbolic_search(lib, (1, 0, 0), 4, interleave=True)
    assert result.lower == result.upper == optimum
