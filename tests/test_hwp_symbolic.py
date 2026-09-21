from dataclasses import replace
from itertools import product

import pytest

from collective_phase.hwp_symbolic import SymbolicLibrary, TOFFOLI_TIMING, TimingTransfer
from collective_phase.hwp_pareto import build_library, Plan
from collective_phase.ir import AngleBinding, ParityTerm, PhaseBlock, PhaseProgram, make_program
from collective_phase.lowering import RotationSynthesizer, GateEvent
from collective_phase.lowering.primitives import exact_toffoli_gate_sequence
from collective_phase.resources import schedule_events, estimate_resources


def native(n, angle='0.173'):
    return make_program('native', n, [1 << i for i in range(n)], AngleBinding('a', angle))


@pytest.fixture(scope='module')
def synth():
    return RotationSynthesizer()


@pytest.mark.parametrize('levels', [(0,0,0), (12,0,3), (0,19,1), (3,4,21), (8,8,8)])
def test_port_transfer_against_actual_event_scheduler(levels):
    gates = exact_toffoli_gate_sequence((0,1,2))
    prefix = [GateEvent('t', (q,)) for q, level in enumerate(levels) for _ in range(level)]
    events = prefix + [GateEvent(k, qs) for k, qs in gates]
    expected = TOFFOLI_TIMING.apply(levels)
    # Per-port identity probes expose final arrival times through the real scheduler.
    schedule = schedule_events(events + [GateEvent('x', (q,)) for q in range(3)])
    assert schedule.event_levels[-3:] == expected
    assert schedule.t_depth == max(expected)
    identity = TimingTransfer.from_gates([('cx', (0,1))], 3)
    assert identity.apply(levels)[2] == levels[2]


@pytest.mark.parametrize('size', range(1,9))
@pytest.mark.parametrize('ordering', ['staged','readiness'])
def test_counts_graph_and_workspace_against_emission(size, ordering, synth):
    symbolic = SymbolicLibrary(native(size, 'pi/4'), 1e-4, synth, orderings=(ordering,))
    eager = build_library(symbolic.program, 1e-4, synth, orderings=(ordering,))
    assert len(symbolic.options) == len(eager.options)
    for o, actual in zip(symbolic.options, eager.options):
        assert symbolic.evaluate(o).exact
        assert symbolic.evaluate(o).lower == actual.resources
        assert (o.terms, o.footprint, o.layout, o.ordering, o.allowance) == (
            actual.terms, actual.footprint, actual.layout, actual.ordering, actual.allowance)
        assert o.arithmetic_t == (14 * (len(o.local_masks)-len(o.local_masks).bit_count()))
        graph = symbolic.graph(o)
        assert all(end == len(graph.operations) for _, _, _, end in graph.lifetimes)
    assert symbolic.stats['templates_materialized'] == 0
    assert symbolic.stats['rotations_refined'] == 0


def programs():
    a, b = AngleBinding('a','0.173'), AngleBinding('b','pi/8')
    return [native(4), make_program('overlap',3,[3,5,6],a),
        make_program('repeat',2,[1,1,2,2],a),
        PhaseProgram('complement',2,(a,), (PhaseBlock('b',(
            ParityTerm('x',1,'a',offset=True,coefficient=-1),
            ParityTerm('y',2,'a',offset=True,coefficient=-1))),)),
        PhaseProgram('heterogeneous',3,(a,b), (PhaseBlock('b',(
            ParityTerm('x',1,'a',coefficient=3), ParityTerm('y',2,'a',coefficient=3),
            ParityTerm('z',4,'b'))),)),
        make_program('empty',1,[1,1],a,coefficients=[1,-1])]


@pytest.mark.parametrize('program', programs())
def test_descriptor_precision_refinement_and_eager_agreement(program, synth):
    symbolic = SymbolicLibrary(program, 1e-4, synth, orderings=('staged','readiness'))
    eager = build_library(program, 1e-4, synth, orderings=('staged','readiness'))
    assert len(symbolic.options) == len(eager.options)
    for o, actual in zip(symbolic.options, eager.options):
        bound = symbolic.evaluate(o)
        assert all(x <= y for x,y in zip(bound.lower, actual.resources))
        if not bound.exact:
            assert bound.upper is None
        for req, rotation in zip(o.requests, actual.lowered.application_rotations):
            assert req.angle.cache_key == rotation.angle_key
            assert req.tolerance == rotation.tolerance
        symbolic.resolve(o)
        assert symbolic.evaluate(o).lower == actual.resources
    assert symbolic.stats['templates_materialized'] == 0
    assert symbolic.stats['rotations_refined'] == len({r.key for o in symbolic.options
        for r in o.requests if not r.angle.is_exact_clifford_t})
    assert len({o.template_key for o in symbolic.options}) == symbolic.stats['graphs']


@pytest.mark.parametrize('layout,ordering', product(['in_place_inputs','copied_parities'], ['staged','readiness']))
def test_generic_finalists_dense_verification(layout, ordering, synth):
    lib = SymbolicLibrary(native(3), 1e-4, synth, orderings=(ordering,))
    o = next(o for o in lib.options if o.terms == lib.full_mask and o.layout == layout)
    r = lib.resolve(o).lower
    lowered, proof = lib.emit(Plan(r, ((o.id,),)), memory_cap_bytes=64*1024*1024)
    assert proof['status'] == 'verified_lowered_dense'
    resources = estimate_resources(lowered)
    assert (resources.t_count, resources.t_depth, resources.peak_workspace) == r
    assert lowered.error_bound <= 1e-4
    assert lib.stats['templates_materialized'] == lib.stats['circuits_verified'] == 1


def test_descriptor_stage_does_not_construct_or_synthesize(monkeypatch):
    import collective_phase.hwp_symbolic as module
    def forbidden(*args, **kwargs):
        raise AssertionError('descriptor performed construction')
    monkeypatch.setattr(module, '_emit_adder_batch', forbidden)
    monkeypatch.setattr(module, 'compile_hwp_adder_unitary', forbidden)
    monkeypatch.setattr(RotationSynthesizer, 'synthesize', forbidden)
    lib = SymbolicLibrary(native(8), 1e-4, RotationSynthesizer())
    assert len(lib.options) == 502
    assert not lib.graphs and not lib.materialized and not lib.rotations


def test_parity_structure_and_contract_separate_cache_keys():
    a = AngleBinding('a','0.173')
    lib = SymbolicLibrary(make_program('p',3,[1,3,5,7],a),1e-4,RotationSynthesizer())
    pairs = [o for o in lib.options if len(o.local_masks)==2]
    assert len({o.template_key for o in pairs}) > 1
    other = SymbolicLibrary(lib.program,1e-4,RotationSynthesizer(seed=1))
    assert lib.options[0].requests[0].key != other.options[0].requests[0].key
    assert lib.fingerprint(4,None) != other.fingerprint(4,None)
