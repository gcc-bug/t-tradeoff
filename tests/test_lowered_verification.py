from dataclasses import replace
import math

import pytest

from collective_phase.baselines import (
    compile_hwp_macro_legacy,
    compile_independent,
)
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import GateEvent, RotationSynthesizer, lower_candidate
from collective_phase.verification import verify_lowered_circuit


def _generic_lowered():
    program = make_program(
        "generic", 2, [3, 1], AngleBinding("theta", "0.173")
    )
    candidate = compile_independent(
        program, CompilationConstraints(0, "unitary_clifford_t")
    )
    return lower_candidate(candidate, 1e-4, RotationSynthesizer())


def _mutate_event(lowered, index, event):
    events = list(lowered.events)
    events[index] = event
    return replace(lowered, events=events)


def test_lowered_verifier_rejects_t_to_t_dagger_mutation():
    lowered = _generic_lowered()
    index = next(
        i
        for i, event in enumerate(lowered.events)
        if isinstance(event, GateEvent) and event.kind == "t"
    )
    mutated = _mutate_event(
        lowered, index, GateEvent("tdg", lowered.events[index].qubits)
    )
    assert verify_lowered_circuit(mutated, 1e-4).status == "verification_failure"


def test_lowered_verifier_rejects_reversed_cnot_and_missing_cleanup():
    lowered = _generic_lowered()
    indices = [
        i
        for i, event in enumerate(lowered.events)
        if isinstance(event, GateEvent) and event.kind == "cx"
    ]
    event = lowered.events[indices[0]]
    reversed_cx = _mutate_event(
        lowered, indices[0], GateEvent("cx", tuple(reversed(event.qubits)))
    )
    assert (
        verify_lowered_circuit(reversed_cx, 1e-4).status
        == "verification_failure"
    )
    missing_cleanup = replace(
        lowered,
        events=[
            event
            for index, event in enumerate(lowered.events)
            if index != indices[-1]
        ],
    )
    assert (
        verify_lowered_circuit(missing_cleanup, 1e-4).status
        == "verification_failure"
    )


def test_lowered_verifier_rejects_global_phase_and_nan_mutations():
    lowered = _generic_lowered()
    shifted = replace(
        lowered,
        lowering_global_phase=lowered.lowering_global_phase + 0.1,
    )
    assert verify_lowered_circuit(shifted, 1e-4).status == "verification_failure"
    nan_error = replace(lowered, error_bound=math.nan)
    assert verify_lowered_circuit(nan_error, 1e-4).status == "verification_failure"


def test_macro_cannot_be_marked_as_emitted_evidence():
    program = make_program(
        "three", 2, [1, 2, 3], AngleBinding("theta", "pi/4")
    )
    candidate = compile_hwp_macro_legacy(
        program, CompilationConstraints(8, "unitary_clifford_t")
    )
    candidate = replace(candidate, accounting_status="emitted")
    lowered = lower_candidate(candidate, 1e-4, RotationSynthesizer())
    result = verify_lowered_circuit(lowered, 1e-4)
    assert result.status == "macro_not_verified"
    assert result.macro_free is False


def test_dense_preflight_uses_compositional_scope_without_allocating():
    lowered = _generic_lowered()
    result = verify_lowered_circuit(
        lowered, 1e-4, memory_cap_bytes=1
    )
    assert result.status == "verified_lowered_compositional"
    assert result.operator_norm_error is None
