from dataclasses import replace

from collective_phase.adapters import FeynmanAdapter, PyZXAdapter
from collective_phase.baselines import compile_hwp_adder_unitary
from collective_phase.baselines.common import CompilationConstraints
from collective_phase.ir import AngleBinding, make_program
from collective_phase.lowering import GateEvent, RotationSynthesizer, lower_candidate
from collective_phase.resources import estimate_resources, schedule_events
from collective_phase.verification import verify_optimized_lowered_circuit


def _hwp_lowered():
    program = make_program(
        "four", 4, [1, 2, 4, 8], AngleBinding("theta", "pi/4")
    )
    candidate = compile_hwp_adder_unitary(
        program,
        CompilationConstraints(8, "unitary_clifford_t"),
        batch_limit=2,
    )
    return lower_candidate(candidate, 1e-4, RotationSynthesizer())


def test_pyzx_exact_rewrite_is_verified_and_recounted():
    source = _hwp_lowered()
    result = PyZXAdapter(seed=0).optimize(source, "zx_extract")
    assert result.verified, result.reason
    assert result.lowered is not None
    verification = verify_optimized_lowered_circuit(source, result.lowered, 1e-4)
    assert verification.status == "verified_lowered_external_dense"
    before = estimate_resources(source)
    after = estimate_resources(result.lowered)
    assert after.t_count < before.t_count
    assert after.t_depth < before.t_depth
    assert after.peak_workspace <= before.peak_workspace


def test_external_verifier_rejects_mutated_optimizer_stream():
    source = _hwp_lowered()
    result = PyZXAdapter(seed=0).optimize(source, "todd")
    assert result.lowered is not None
    mutated = replace(
        result.lowered,
        events=[GateEvent("tdg", (0,)), *result.lowered.events],
    )
    verification = verify_optimized_lowered_circuit(source, mutated, 1e-4)
    assert verification.status == "verification_failure"


def test_schedule_identifies_critical_t_events_and_slack():
    events = [
        GateEvent("t", (0,)),
        GateEvent("t", (0,)),
        GateEvent("t", (1,)),
    ]
    schedule = schedule_events(events)
    assert schedule.t_depth == 2
    assert schedule.critical_t_events == (0, 1)
    assert schedule.event_slack == (0, 0, 1)


def test_feynman_subprocess_boundary_accepts_verified_dotqc(tmp_path):
    executable = tmp_path / "feynopt"
    executable.write_text(
        """#!/bin/sh
if [ "$1" = "-h" ]; then
  echo '-tpar'
  exit 0
fi
echo '# Result (0.1ms):'
echo '.v q0'
echo '.i q0'
echo '.o q0'
echo 'BEGIN'
echo 'T q0'
echo 'END'
""",
        encoding="ascii",
    )
    executable.chmod(0o755)
    program = make_program("one", 1, [1], AngleBinding("theta", "pi/4"))
    candidate = compile_hwp_adder_unitary(
        program, CompilationConstraints(0, "unitary_clifford_t")
    )
    source = lower_candidate(candidate, 1e-4, RotationSynthesizer())
    result = FeynmanAdapter(executable, revision="test").optimize(source, "tpar")
    assert result.verified, result.reason
    assert result.lowered is not None
    assert (
        verify_optimized_lowered_circuit(source, result.lowered, 1e-4).status
        == "verified_lowered_external_dense"
    )
