from dataclasses import replace
import multiprocessing
import time

import pytest

from collective_phase.adapters import FeynmanAdapter, PhaseAncillaAdapter, PyZXAdapter
from collective_phase.adapters.phase_ancilla import phase_regions
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


def _ccz_phase_lowered():
    from collective_phase.baselines import compile_independent

    program = make_program(
        "ccz-phase", 3, [1, 2, 4, 3, 5, 6, 7],
        AngleBinding("theta", "pi/4"),
        coefficients=[1, 1, 1, -1, -1, -1, 1],
    )
    return lower_candidate(
        compile_independent(program, CompilationConstraints(4, "unitary_clifford_t")),
        1e-4, RotationSynthesizer(),
    )


def test_clean_scratch_phase_rewrite_measures_tradeoff_and_rejects_dirty_output():
    source = _ccz_phase_lowered()
    region = phase_regions(source.events)[0]
    adapter = PhaseAncillaAdapter()
    assert estimate_resources(source).t_depth == 5
    for scratch, depth in ((1, 4), (2, 2), (4, 1)):
        result = adapter.optimize_region(source, region, scratch)
        assert result.verified, result.reason
        assert result.lowered is not None
        assert estimate_resources(result.lowered).peak_workspace == scratch
        assert estimate_resources(result.lowered).t_depth == depth
        assert verify_optimized_lowered_circuit(source, result.lowered, 1e-4).status.startswith("verified_lowered_")
        dirty = replace(
            result.lowered,
            events=[*result.lowered.events[:region[0]],
                    GateEvent("cx", (0, source.candidate.program.qubit_count + source.candidate.workspace_qubits)),
                    *result.lowered.events[region[0]:]],
        )
        assert verify_optimized_lowered_circuit(source, dirty, 1e-4, memory_cap_bytes=1).status == "verification_failure"


def test_distinct_phase_regions_reuse_certified_clean_scratch():
    source = _hwp_lowered()
    live = source.candidate.program.qubit_count + source.candidate.workspace_qubits
    adapter = PhaseAncillaAdapter()
    first_region = phase_regions(source.events)[0]
    first = adapter.optimize_region(source, first_region, 2)
    assert first.verified, first.reason
    assert first.lowered is not None
    first_metadata = first.lowered.optimization
    assert first_metadata is not None
    assert first_metadata["allocated_scratch_wire_ids"] == [live, live + 1]
    assert first_metadata["released_scratch_wire_ids"] == [live, live + 1]
    assert verify_optimized_lowered_circuit(
        source, first.lowered, 1e-4
    ).status.startswith("verified_lowered_")

    second_region = phase_regions(first.lowered.events)[-1]
    second = adapter.optimize_region(first.lowered, second_region, 2)
    assert second.verified, second.reason
    assert second.lowered is not None
    second_metadata = second.lowered.optimization
    assert second_metadata is not None
    assert second_metadata["allocated_scratch_wire_ids"] == []
    assert second_metadata["reused_scratch_wire_ids"] == [live, live + 1]
    assert second_metadata["released_scratch_wire_ids"] == [live, live + 1]
    assert second.lowered.allocated_qubits == first.lowered.allocated_qubits
    assert verify_optimized_lowered_circuit(
        first.lowered, second.lowered, 1e-4, ancestry=(source,)
    ).status.startswith("verified_lowered_")


def test_optimized_parent_requires_valid_full_chain():
    source = _ccz_phase_lowered()
    parent = PhaseAncillaAdapter().optimize_region(source, phase_regions(source.events)[0], 1).lowered
    assert parent is not None
    child = PyZXAdapter(seed=0).optimize(parent, "full_optimize").lowered
    assert child is not None
    assert verify_optimized_lowered_circuit(parent, child, 1e-4).status == "lowered_evidence_unsupported"
    assert verify_optimized_lowered_circuit(parent, child, 1e-4, ancestry=(source,), memory_cap_bytes=1).status.startswith("verified_lowered_")
    corrupted_parent = replace(parent, events=[GateEvent("tdg", (0,)), *parent.events])
    assert verify_optimized_lowered_circuit(corrupted_parent, child, 1e-4, ancestry=(source,), memory_cap_bytes=1).status == "verification_failure"
    corrupted_child = replace(child, events=[GateEvent("tdg", (0,)), *child.events])
    assert verify_optimized_lowered_circuit(parent, corrupted_child, 1e-4, ancestry=(source,), memory_cap_bytes=1).status == "verification_failure"


def test_pyzx_exact_rewrite_is_verified_and_recounted():
    source = _hwp_lowered()
    result = PyZXAdapter(seed=0).optimize(source, "zx_extract")
    assert result.verified, result.reason
    assert result.lowered is not None
    assert result.lowered.optimization["semantic_boundaries"] == "invalidated"
    assert result.lowered.optimization["clean_scratch_pool"] == []
    verification = verify_optimized_lowered_circuit(source, result.lowered, 1e-4)
    assert verification.status == "verified_lowered_external_dense"
    before = estimate_resources(source)
    after = estimate_resources(result.lowered)
    assert after.t_count < before.t_count
    assert after.t_depth < before.t_depth
    assert after.peak_workspace <= before.peak_workspace


def test_pyzx_worker_enforces_search_deadline(monkeypatch):
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("worker monkeypatch requires fork")
    import pyzx

    monkeypatch.setattr(pyzx.optimize, "full_optimize", lambda circuit: time.sleep(2))
    result = PyZXAdapter(seed=0).optimize(
        _hwp_lowered(), "full_optimize", timeout_seconds=0.05
    )
    assert result.status == "timed_out"
    assert result.lowered is None
    assert result.backend_seconds < 1


def test_external_verifier_rejects_mutated_optimizer_stream():
    source = _hwp_lowered()
    result = PyZXAdapter(seed=0).optimize(source, "full_optimize")
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


def test_feynman_subprocess_boundary_accepts_verified_dotqc(tmp_path, monkeypatch):
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
    if "fork" in multiprocessing.get_all_start_methods():
        from collective_phase.adapters import feynman as feynman_module

        monkeypatch.setattr(feynman_module, "equivalence_phase", lambda *args: time.sleep(2))
        timed = FeynmanAdapter(executable, revision="test").optimize(
            source, "tpar", timeout_seconds=0.05,
        )
        assert timed.status == "timed_out"
        assert timed.lowered is None
