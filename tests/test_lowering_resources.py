import cmath
import math

import numpy as np
import pytest

from collective_phase.baselines import compile_catalyzed_hwp, compile_hwp, compile_independent
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.candidates import compile_dependent_triples
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import GateEvent, RotationSynthesizer, lower_candidate
from collective_phase.resources import estimate_resources


def _apply_gate(state, event, total_qubits):
    output = np.zeros_like(state)
    one_qubit = {
        "h": np.array([[1, 1], [1, -1]], complex) / math.sqrt(2),
        "t": np.diag([1, cmath.exp(1j * math.pi / 4)]),
        "tdg": np.diag([1, cmath.exp(-1j * math.pi / 4)]),
        "s": np.diag([1, 1j]),
        "sdg": np.diag([1, -1j]),
        "z": np.diag([1, -1]),
        "x": np.array([[0, 1], [1, 0]], complex),
    }
    if event.kind in one_qubit:
        target = event.qubits[0]
        matrix = one_qubit[event.kind]
        for basis in range(1 << total_qubits):
            source_bit = (basis >> target) & 1
            for target_bit in (0, 1):
                destination = (basis & ~(1 << target)) | (target_bit << target)
                output[destination] += matrix[target_bit, source_bit] * state[basis]
        return output
    if event.kind == "cx":
        control, target = event.qubits
        for basis, value in enumerate(state):
            destination = basis ^ ((1 << target) if (basis >> control) & 1 else 0)
            output[destination] += value
        return output
    raise AssertionError(event.kind)


def test_unitary_candidate_is_fully_emitted_and_matches_dense_target():
    program = make_program("triple", 2, [1, 2, 3], AngleBinding("theta", "pi/4"))
    candidate = compile_dependent_triples(
        program, CompilationConstraints(3, "unitary_clifford_t")
    )
    lowered = lower_candidate(candidate, 1e-4, RotationSynthesizer())
    assert all(isinstance(event, GateEvent) for event in lowered.events)
    assert estimate_resources(lowered).t_count == 14

    total = program.qubit_count + candidate.workspace_qubits
    state = np.zeros(1 << total, complex)
    state[:4] = np.array([1, 2j, -0.5, 0.7j])
    state /= np.linalg.norm(state)
    original = state.copy()
    for event in lowered.events:
        state = _apply_gate(state, event, total)
    expected = np.zeros_like(state)
    for x in range(4):
        expected[x] = original[x] * cmath.exp(1j * program.phase_radians(x))
    phase = candidate.global_phase + lowered.lowering_global_phase
    # Exact P gates carry no lowering phase; retain this expression as a
    # regression guard when generic synthesis is used elsewhere.
    expected *= cmath.exp(1j * (phase - candidate.global_phase))
    assert np.linalg.norm(state - expected) < 1e-10


def test_measurement_hwp_uses_published_adder_count_and_is_labeled_estimate():
    program = make_program("three", 2, [1, 2, 3], AngleBinding("theta", "pi/4"))
    candidate = compile_hwp(
        program, CompilationConstraints(8, "measurement_assisted_clifford_t")
    )
    resources = estimate_resources(
        lower_candidate(candidate, 1e-4, RotationSynthesizer())
    )
    assert resources.accounting_status == "estimated_macro"
    assert resources.measurement_count == 1  # M - popcount(M) for M=3
    assert resources.t_count == 5  # 4 arithmetic T plus P(pi/4); P(pi/2) is Clifford


def test_catalyst_preparation_and_reuse_are_separate():
    program = make_program("three", 2, [1, 2, 3], AngleBinding("theta", "pi/4"))
    candidate = compile_catalyzed_hwp(
        program,
        CompilationConstraints(8, "measurement_assisted_clifford_t", catalyst_reuse_count=10),
    )
    resources = estimate_resources(
        lower_candidate(candidate, 1e-4, RotationSynthesizer())
    )
    assert resources.reuse_count == 10
    assert resources.preparation_t > 0
    assert resources.t_count == resources.preparation_t + 10 * resources.application_t
    assert resources.t_depth == resources.preparation_depth + 10 * resources.application_depth


def test_generic_pygridsynth_rotation_respects_operator_norm_budget(tmp_path):
    pytest.importorskip("pygridsynth")
    angle = AngleBinding("theta", "0.173").scaled(1)
    result = RotationSynthesizer(tmp_path / "cache.json").synthesize(angle, 1e-4)
    assert result.backend == "pygridsynth"
    assert result.actual_operator_error <= 1e-4
    assert result.t_count > 0


def test_generic_lowering_retains_backend_global_phase_tokens(tmp_path):
    pytest.importorskip("pygridsynth")
    program = make_program("one", 1, [1], AngleBinding("theta", "0.173"))
    candidate = compile_independent(
        program, CompilationConstraints(0, "unitary_clifford_t")
    )
    lowered = lower_candidate(
        candidate, 1e-4, RotationSynthesizer(tmp_path / "cache.json")
    )
    state = np.array([0.3 + 0.2j, -0.7 + 0.1j], complex)
    state /= np.linalg.norm(state)
    actual = state.copy()
    for event in lowered.events:
        assert isinstance(event, GateEvent)
        actual = _apply_gate(actual, event, 1)
    actual *= cmath.exp(
        1j * (candidate.global_phase + lowered.lowering_global_phase)
    )
    expected = state * np.array([1, cmath.exp(1j * 0.173)])
    assert np.linalg.norm(actual - expected) <= 1e-4
