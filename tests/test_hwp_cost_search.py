from dataclasses import replace
from fractions import Fraction as F
from itertools import product

import pytest

from collective_phase.hwp_cost_search import (
    CertifiedInequality, Model, completion_bounds, cost, rational, search, transferred_bound, weights,
)
from collective_phase.hwp_pareto import Plan, build_library, emit, frontier
from collective_phase.ir import AngleBinding, ParityTerm, PhaseBlock, PhaseProgram, make_program
from collective_phase.lowering import RotationSynthesizer


@pytest.fixture(scope='module')
def models():
    synth = RotationSynthesizer()
    programs = [make_program('native',3,[1,2,4],AngleBinding('a','0.173')),
                make_program('overlap',3,[3,5,6],AngleBinding('a','0.173')),
                PhaseProgram('boundaries',2,(AngleBinding('a','pi/4'),),(
                    PhaseBlock('a',(ParityTerm('p',1,'a'),)),
                    PhaseBlock('b',(ParityTerm('q',2,'a'),))))]
    return [Model(build_library(p,1e-4,synth,max_batch=3)) for p in programs]


def enumerate_resources(lib, remaining, cap):
    """Independent exact partitions, then all set partitions into legal waves.

    This oracle neither calls canonical_waves nor uses state dominance or DP.
    It also supports every partial remaining-term state for lower-bound checks.
    """
    def partitions(left):
        if left == 0:
            yield []
            return
        anchor = left & -left
        for o in lib.options:
            if o.terms & anchor and o.terms & left == o.terms and o.resources[2] <= cap:
                for tail in partitions(left ^ o.terms):
                    yield [o,*tail]
    found = set()
    for blocks in partitions(remaining):
        def waves(i, groups):
            if i == len(blocks):
                found.add((sum(o.resources[0] for o in blocks),
                           sum(max(o.resources[1] for o in w) for w in groups),
                           max((sum(o.resources[2] for o in w) for w in groups), default=0)))
                return
            o = blocks[i]
            for j,w in enumerate(groups):
                if (all(o.boundary == x.boundary and not o.footprint & x.footprint for x in w)
                        and sum(x.resources[2] for x in w)+o.resources[2] <= cap):
                    waves(i+1, groups[:j]+[w+[o]]+groups[j+1:])
            waves(i+1,groups+[[o]])
        waves(0,[])
    return found


W = [(1,0,0),(0,1,0),('0.8','0.1','0.1'),('1/3','1/3','1/3'),(0,0,1)]


def test_exact_optima_and_reconstruction(models):
    for model, cap in product(models,[0,2,4]):
        exact = frontier(model.library,cap)
        assert exact.complete
        for pref, depth in product(W,[None,100,0]):
            w = weights(pref)
            eligible = [p for p in exact.plans if depth is None or p.resources[1]<=depth]
            optimum = min((cost(p.resources,w) for p in eligible), default=None)
            for structural in (False,True):
                result = search(model,w,cap,depth,structural=structural)
                if optimum is None:
                    assert result.status=='INFEASIBLE'
                else:
                    assert result.status=='OPTIMAL'
                    assert result.lower==result.upper==optimum
                    lowered,proof = emit(model.library,result.plan)
                    assert proof['status'].startswith('verified_lowered_')
                    assert lowered.error_bound<=model.library.total_error


def test_every_partial_structural_bound_against_independent_oracle(models):
    for model, cap in product(models,[0,2,4]):
        lib = model.library
        options = [o for o in lib.options if o.resources[2]<=cap]
        for remaining in range(lib.full_mask+1):
            bound = completion_bounds(lib,remaining,options)
            completions = enumerate_resources(lib,remaining,cap)
            assert bound is not None
            for r in completions:
                assert all(x<=y for x,y in zip(bound,r))
            for pref,prefix in product(W,[(0,0,0),(10,20,3)]):
                w=weights(pref)
                lower=cost((prefix[0]+bound[0],prefix[1]+bound[1],max(prefix[2],bound[2])),w)
                optimum=min(cost((prefix[0]+r[0],prefix[1]+r[1],max(prefix[2],r[2])),w) for r in completions)
                assert lower<=optimum
        assert completion_bounds(lib,lib.full_mask,[]) is None


def test_transferred_bounds_and_bad_certificates(models):
    for model in models:
        archive=[CertifiedInequality.from_result(search(model,p,4)) for p in W]
        oracle=enumerate_resources(model.library,model.library.full_mask,4)
        for pref in [('0.6','0.3','0.1'),('0.2','0.5','0.3'),('0.4','0.2','0.4')]:
            w=weights(pref)
            lower=transferred_bound(archive,w,model.query_fingerprint(4,None))
            optimum=min(cost(r,w) for r in oracle)
            assert lower<=optimum
            assert search(model,w,4,certificates=archive).upper==optimum
        cert=archive[0]
        for bad in [replace(cert,bound=cert.bound+1),replace(cert,bound=float(cert.bound)),replace(cert,coefficients=weights((0,1,0))),
                    replace(cert,fingerprint='bad')]:
            with pytest.raises(ValueError):
                search(model,(1,0,0),4,certificates=[bad])
        with pytest.raises(ValueError,match='fingerprint'):
            search(model,(1,0,0),3,certificates=archive)
        with pytest.raises(ValueError,match='fingerprint'):
            search(model,(1,0,0),4,100,certificates=archive)
        with pytest.raises(ValueError):
            weights((0,0,0))
        assert rational('0.1')==F(1,10)


class TickClock:
    def __init__(self):
        self.value=0
    def __call__(self):
        self.value+=0.001
        return self.value


def test_timeout_during_expansion_and_between_nodes(models):
    model=models[0]
    singles=[o for o in model.library.options if o.layout=='direct']
    seed=Plan((sum(o.resources[0] for o in singles),sum(o.resources[1] for o in singles),0),
              tuple((o.id,) for o in singles))
    optimum=min(r[0] for r in enumerate_resources(model.library,model.library.full_mask,4))
    active=between=False
    for deadline in [0,0.006,0.01,0.02,0.04,0.08,0.16]:
        result=search(model,(1,0,0),4,seeds=[seed],structural=False,
                      timeout_seconds=deadline,clock=TickClock())
        assert result.lower<=optimum<=result.upper
        if result.reason=='TIMEOUT':
            assert result.status=='FEASIBLE'
            active |= result.stats['pending_expansion_at_timeout']
            between |= not result.stats['pending_expansion_at_timeout']
    assert active and between
    result=search(model,(1,0,0),4,0,structural=False,timeout_seconds=0)
    assert result.status=='TIMEOUT' and result.plan is None and result.lower==0
    assert search(model,(1,0,0),4,0).status=='INFEASIBLE'
    # A feasible incumbent upper bound must never become a certificate lower bound.
    result=search(model,(1,0,0),4,seeds=[seed],structural=False,timeout_seconds=0)
    assert result.lower==0<result.upper
    with pytest.raises(ValueError,match='exact'):
        search(model,(1,0,0),4,seeds=[replace(seed,resources=tuple(map(float,seed.resources)))])
    cert=CertifiedInequality.from_result(result)
    with pytest.raises(ValueError):
        CertifiedInequality.from_result(replace(result,lower=float(result.lower)))
    with pytest.raises(ValueError):
        search(model,(1,0,0),4,certificates=[replace(cert,bound=result.upper)])


def test_zero_cost_tolerance_and_verification_failure(models):
    model=models[0]
    result=search(model,(0,0,1),4)
    assert result.lower==result.upper==0 and result.relative_gap is None
    result=search(model,(1,1,1),4,tolerance='0.05')
    assert result.upper<=(1+F(1,20))*result.lower
    with pytest.raises(ValueError,match='coverage'):
        search(model,(1,0,0),4,seeds=[Plan((0,0,0))])
    zero=make_program('zero',1,[1,1],AngleBinding('a','0.173'),coefficients=[1,-1])
    result=search(Model(build_library(zero,1e-4,RotationSynthesizer())),(1,0,0),0)
    assert result.status=='OPTIMAL' and result.plan.resources==(0,0,0)


def test_unsupported_witness_is_a_constrained_win_only():
    program=make_program('overlapping_6',3,[1,2,3,4,5,6],AngleBinding('a','0.173'))
    model=Model(build_library(program,1e-4,RotationSynthesizer(),max_batch=8))
    result=search(model,(1,0,0),3,200)
    assert result.status=='OPTIMAL' and result.plan.resources==(284,166,3)
    emit(model.library,result.plan)
    midpoint=tuple(F(x+y,2) for x,y in zip((228,112,4),(312,156,0)))
    assert all(x<y for x,y in zip(midpoint,result.plan.resources))
