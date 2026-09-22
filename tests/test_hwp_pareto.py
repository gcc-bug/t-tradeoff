from dataclasses import replace

import pytest

from collective_phase.hwp_pareto import (
    Plan, baseline_frontiers, build_library, emit, frontier, pareto,
)
from collective_phase.ir import AngleBinding, ParityTerm, PhaseBlock, PhaseProgram, make_program
from collective_phase.lowering import GateEvent, LoweredCircuit, RotationSynthesizer
from collective_phase.circuit import Candidate
from collective_phase.verification import verify_lowered_circuit


@pytest.fixture(scope="module")
def synth():
    return RotationSynthesizer()


def native(n, angle="pi/4"):
    return make_program("native", n, [1 << i for i in range(n)], AngleBinding("theta", angle))


def brute_force(library, cap):
    """Independent partitions then set partitions of blocks into waves; no DP.

    It deliberately does not use the production wave generator, canonical-wave
    recurrence, or its dominance routine.
    """
    def partitions(left):
        if not left:
            yield []
            return
        term = min(left)
        for opt in library.options:
            subset = {i for i in range(len(library.terms)) if opt.terms >> i & 1}
            if term in subset and subset <= left:
                for rest in partitions(left - subset):
                    yield [opt, *rest]
    found = set()
    for blocks in partitions(set(range(len(library.terms)))):
        def assign(index, waves):
            if index == len(blocks):
                found.add((sum(o.resources[0] for o in blocks),
                           sum(max(o.resources[1] for o in w) for w in waves),
                           max((sum(o.resources[2] for o in w) for w in waves), default=0)))
                return
            opt = blocks[index]
            if opt.resources[2] > cap:
                return
            for i, wave in enumerate(waves):
                if all(o.boundary == opt.boundary and not o.footprint & opt.footprint for o in wave):
                    if sum(o.resources[2] for o in wave) + opt.resources[2] <= cap:
                        assign(index + 1, waves[:i] + [wave + [opt]] + waves[i + 1:])
            assign(index + 1, waves + [[opt]])
        assign(0, [])
    return {r for r in found if not any(s != r and all(a <= b for a, b in zip(s, r)) for s in found)}


@pytest.mark.parametrize("program,cap", [
    (native(4, "0.173"), 4),
    (native(5, "0.173"), 4),
    (native(6), 3),
    (make_program("parity", 3, [3, 5, 6], AngleBinding("theta", "0.173")), 4),
])
def test_exact_frontier_agrees_with_independent_exhaustive_oracle(program, cap, synth):
    library = build_library(program, 1e-4, synth)
    result = frontier(library, cap)
    assert result.complete
    assert {p.resources for p in result.plans} == brute_force(library, cap)
    for plan in result.plans:
        lowered, proof = emit(library, plan, memory_cap_bytes=256 * 1024)
        assert proof["status"].startswith("verified_lowered_")
        rebuilt = LoweredCircuit.from_dict(lowered.to_dict(),
                    Candidate.from_dict(lowered.candidate.to_dict(), program))
        assert verify_lowered_circuit(rebuilt, 1e-4, memory_cap_bytes=1).status.startswith("verified_lowered_")


def test_scratch_is_disjoint_within_wave_and_reused_across_waves(synth):
    library = build_library(native(6, "0.173"), 1e-4, synth, max_batch=3)
    first = next(o for o in library.options if o.terms == 7 and o.layout == "in_place_inputs")
    second = next(o for o in library.options if o.terms == 56 and o.layout == "in_place_inputs")
    t, d, a = first.resources
    sequential, _ = emit(library, Plan((2*t, 2*d, a), ((first.id,), (second.id,))))
    parallel, _ = emit(library, Plan((2*t, d, 2*a), ((first.id, second.id),)))
    seq = sequential.candidate.parameters["wave_schedule"]
    par = parallel.candidate.parameters["wave_schedule"]
    assert seq[0]["blocks"][0]["scratch"] == seq[1]["blocks"][0]["scratch"]
    assert set(par[0]["blocks"][0]["scratch"]).isdisjoint(par[0]["blocks"][1]["scratch"])
    assert sequential.error_bound <= 1e-4 and parallel.error_bound <= 1e-4


def test_nonuniform_precision_composition_and_mutation_rejection(synth):
    library = build_library(native(5, "0.173"), 1e-4, synth)
    opts = [next(o for o in library.options if o.terms == mask and o.layout == layout)
            for mask, layout in [(7, "in_place_inputs"), (8, "direct"), (16, "direct")]]
    plan = Plan((sum(o.resources[0] for o in opts), max(o.resources[1] for o in opts),
                 sum(o.resources[2] for o in opts)), (tuple(o.id for o in opts),))
    lowered, _ = emit(library, plan)
    assert len({r.tolerance for r in lowered.application_rotations}) > 1
    rotations = list(lowered.application_rotations)
    rotations[0] = replace(rotations[0], requested_error=rotations[0].requested_error * 2)
    assert verify_lowered_circuit(replace(lowered, application_rotations=rotations), 1e-4).status == "verification_failure"
    params = dict(lowered.candidate.parameters)
    blocks = [dict(b) for b in params["term_error_blocks"]]
    blocks[1]["term_ids"] = blocks[0]["term_ids"]
    params["term_error_blocks"] = blocks
    bad = replace(lowered, candidate=replace(lowered.candidate, parameters=params))
    assert verify_lowered_circuit(bad, 1e-4, memory_cap_bytes=1).status == "verification_failure"
    events = list(lowered.events)
    i = next(i for i, e in enumerate(events) if e.kind == "t")
    events[i] = GateEvent("tdg", events[i].qubits)
    assert verify_lowered_circuit(replace(lowered, events=events), 1e-4, memory_cap_bytes=1).status == "verification_failure"


def test_original_boundaries_and_zero_normalized_terms(synth):
    program = PhaseProgram("boundaries", 2, (AngleBinding("a", "pi/4"),), (
        PhaseBlock("first", (ParityTerm("p", 1, "a"),)),
        PhaseBlock("second", (ParityTerm("q", 2, "a"),))))
    lib = build_library(program, 1e-4, synth)
    result = frontier(lib, 0)
    assert result.plans[0].resources == (2, 2, 0)
    assert {p.resources for p in result.plans} == brute_force(lib, 0)
    with pytest.raises(ValueError, match="boundary"):
        emit(lib, Plan((2, 1, 0), ((0, 1),)))
    zero = make_program("zero", 1, [1, 1], AngleBinding("a", "0.173"), coefficients=[1, -1])
    empty = build_library(zero, 1e-4, synth)
    plan = frontier(empty, 0).plans[0]
    assert plan.resources == (0, 0, 0)
    assert emit(empty, plan)[0].events == []


def test_coverage_and_query_statuses(synth):
    library = build_library(native(3), 1e-4, synth)
    done = frontier(library, 2)
    assert done.solve(0, 1)["status"] == "OPTIMAL"
    assert done.solve(0, 0)["status"] == "INFEASIBLE"
    assert frontier(library, 2, 0, timeout_seconds=0).status == "TIMEOUT"
    assert frontier(library, 2, timeout_seconds=0).status == "FEASIBLE"
    with pytest.raises(ValueError, match="coverage"):
        emit(library, Plan((1, 1, 0), ((0,),)))
    with pytest.raises(ValueError):
        frontier(library, -1)


def test_strong_baselines_and_template_cache(synth):
    library = build_library(native(4, "0.173"), 1e-4, synth)
    assert library.stats["template_hits"] > 0
    baselines = baseline_frontiers(library, 4)
    assert baselines["complete"]
    exact = frontier(library, 4)
    for plans in baselines["frontiers"].values():
        for plan in plans:
            assert any(all(x <= y for x, y in zip(p.resources, plan.resources)) for p in exact.plans)
            emit(library, plan)


def test_unsupported_pareto_point_is_retained():
    plans = [Plan((10, 10, 0)), Plan((14, 8, 0)), Plan((16, 4, 0))]
    assert len(pareto(plans)) == 3


def test_uniform_baseline_can_leave_remainder_direct(synth):
    library = build_library(native(5, "0.173"), 1e-4, synth)
    baseline = baseline_frontiers(library, 4)
    assert baseline["complete"]
    assert (214, 56, 1) in {p.resources for p in baseline["frontiers"]["uniform"]}


def test_queries_cannot_extrapolate_beyond_solved_caps(synth):
    result = frontier(build_library(native(3), 1e-4, synth), 1, 10)
    with pytest.raises(ValueError, match="range"):
        result.solve(2, 10)
    with pytest.raises(ValueError, match="range"):
        result.solve(1, 11)


def test_affine_constants_and_duplicate_cancellation_survive_composition(synth):
    program = PhaseProgram("affine", 2, (AngleBinding("a", "0.173"),), (
        PhaseBlock("b", (ParityTerm("constant", 0, "a", offset=True),
                         ParityTerm("complement", 1, "a", offset=True),
                         ParityTerm("cancel_a", 2, "a"),
                         ParityTerm("cancel_b", 2, "a", coefficient=-1))),))
    library = build_library(program, 1e-4, synth)
    assert len(library.terms) == 1
    circuit, proof = emit(library, frontier(library, 0).plans[0], memory_cap_bytes=1024*1024)
    assert circuit.candidate.global_phase == pytest.approx(0.346)
    assert proof["status"] == "verified_lowered_dense"


def test_library_and_reference_enumeration_respect_deadlines(synth, monkeypatch):
    from collective_phase.hwp_pareto import _Deadline
    import collective_phase.hwp_pareto as module
    calls = 0
    def stop():
        nonlocal calls
        calls += 1
        raise _Deadline
    with pytest.raises(_Deadline):
        build_library(native(3), 1e-4, synth, check_time=stop)
    assert calls == 1
    lib = build_library(native(3), 1e-4, synth)
    def forbidden(*args):
        raise AssertionError('enumerated after deadline')
    monkeypatch.setattr(module, '_partitions', forbidden)
    result = baseline_frontiers(lib, 4, timeout_seconds=0)
    assert not result['complete'] and result['partitions'] == 0
