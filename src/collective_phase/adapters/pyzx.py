from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import multiprocessing
import random
import time

import pyzx

from ..lowering import LoweredCircuit
from ._pyzx_circuit import circuit_to_events, equivalence_phase, events_to_circuit
from .common import AdapterResult


PYZX_REVISION = "0.9.0"
PYZX_ACTIONS = frozenset({"basic", "full_optimize", "zx_extract"})


def _event_hash(lowered: LoweredCircuit) -> str:
    encoded = json.dumps(
        [event.to_dict() for event in lowered.events],
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _optimize_worker(connection, seed: int, lowered: LoweredCircuit, action: str) -> None:
    try:
        connection.send(PyZXAdapter(seed=seed)._optimize_direct(lowered, action))
    except BaseException as exc:
        connection.send(AdapterResult("pyzx", PYZX_REVISION, action, "failed", 0.0, reason=str(exc)))
    finally:
        connection.close()


class PyZXAdapter:
    def __init__(self, *, seed: int = 0) -> None:
        self.seed = seed

    def optimize(
        self, lowered: LoweredCircuit, action: str, *, timeout_seconds: float | None = None
    ) -> AdapterResult:
        if action not in PYZX_ACTIONS:
            raise ValueError(f"unsupported PyZX action {action!r}")
        if timeout_seconds is None:
            return self._optimize_direct(lowered, action)
        started = time.perf_counter()
        if timeout_seconds <= 0:
            return AdapterResult("pyzx", PYZX_REVISION, action, "timed_out", 0.0, reason="search deadline expired")
        method = "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
        context = multiprocessing.get_context(method)
        reader, writer = context.Pipe(duplex=False)
        process = context.Process(
            target=_optimize_worker, args=(writer, self.seed, lowered, action)
        )
        try:
            process.start()
            writer.close()
            if reader.poll(timeout_seconds):
                try:
                    result = reader.recv()
                except EOFError:
                    result = AdapterResult("pyzx", PYZX_REVISION, action, "failed", 0.0, reason="worker exited without a result")
                process.join(timeout=1)
                return result
            return AdapterResult(
                "pyzx", PYZX_REVISION, action, "timed_out",
                time.perf_counter() - started, reason="PyZX exceeded remaining search time",
            )
        finally:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()
            reader.close()
            writer.close()

    def _optimize_direct(self, lowered: LoweredCircuit, action: str) -> AdapterResult:
        started = time.perf_counter()
        declared_qubits = lowered.allocated_qubits
        if declared_qubits is None:
            declared_qubits = lowered.candidate.program.qubit_count + lowered.candidate.workspace_qubits
        try:
            source = events_to_circuit(lowered.events, declared_qubits)
            random_state = random.getstate()
            random.seed(self.seed)
            try:
                if action == "basic":
                    result = pyzx.optimize.basic_optimization(source.copy())
                elif action == "full_optimize":
                    result = pyzx.optimize.full_optimize(source.copy())
                else:
                    graph = source.to_graph()
                    pyzx.simplify.full_reduce(graph, quiet=True)
                    result = pyzx.extract.extract_circuit(graph).to_basic_gates()
                    result = pyzx.optimize.basic_optimization(result)
            finally:
                random.setstate(random_state)
            phase = equivalence_phase(source, result)
            events = circuit_to_events(result)
            data_qubits = lowered.candidate.program.qubit_count
            allocated_qubits = max(
                data_qubits,
                max((qubit + 1 for event in events for qubit in event.qubits), default=0),
            )
            optimized = replace(
                lowered,
                events=events,
                lowering_global_phase=lowered.lowering_global_phase - phase,
                allocated_qubits=allocated_qubits,
                optimization={
                    "backend": "pyzx",
                    "revision": PYZX_REVISION,
                    "action": action,
                    "scope": "whole_circuit",
                    "semantic_boundaries": "invalidated",
                    "clean_scratch_pool": [],
                    "seed": self.seed,
                    "input_event_hash": _event_hash(lowered),
                    "equivalence": "pyzx_full_reduce_up_to_global_phase",
                    "global_phase_correction": -phase,
                },
            )
            optimized.optimization["output_event_hash"] = _event_hash(optimized)
            return AdapterResult(
                "pyzx",
                PYZX_REVISION,
                action,
                "verified",
                time.perf_counter() - started,
                optimized,
            )
        except Exception as exc:
            return AdapterResult(
                "pyzx",
                PYZX_REVISION,
                action,
                "failed",
                time.perf_counter() - started,
                reason=str(exc),
            )
