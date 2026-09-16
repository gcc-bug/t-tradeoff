from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from ..lowering import GateEvent, LoweredCircuit, MacroEvent
from ._pyzx_circuit import equivalence_phase, events_to_circuit
from .common import AdapterResult


FEYNMAN_ACTIONS = frozenset({"phasefold", "tpar", "apf", "qpf", "ppf"})
_INPUT_GATES = {
    "h": "H",
    "x": "X",
    "z": "Z",
    "s": "S",
    "sdg": "S*",
    "t": "T",
    "tdg": "T*",
    "cx": "cnot",
}
_OUTPUT_GATES = {
    "H": "h",
    "X": "x",
    "Z": "z",
    "S": "s",
    "S*": "sdg",
    "T": "t",
    "T*": "tdg",
    "cnot": "cx",
}


def _event_hash(lowered: LoweredCircuit) -> str:
    encoded = json.dumps(
        [event.to_dict() for event in lowered.events],
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _dotqc(lowered: LoweredCircuit, qubit_count: int) -> str:
    names = " ".join(f"q{index}" for index in range(qubit_count))
    lines = [f".v {names}", f".i {names}", f".o {names}", "BEGIN"]
    for event in lowered.events:
        if isinstance(event, MacroEvent):
            raise ValueError("Feynman requires a fully emitted gate stream")
        try:
            gate = _INPUT_GATES[event.kind]
        except KeyError as exc:
            raise ValueError(f"Feynman adapter does not support {event.kind!r}") from exc
        lines.append(gate + " " + " ".join(f"q{value}" for value in event.qubits))
    lines.extend(["END", ""])
    return "\n".join(lines)


def _parse_dotqc(output: str, qubit_count: int) -> list[GateEvent]:
    lines = [line.strip() for line in output.splitlines()]
    try:
        start = lines.index("BEGIN")
    except ValueError:
        try:
            start = lines.index("BEGIN ")
        except ValueError as exc:
            raise ValueError("Feynman output has no circuit body") from exc
    events: list[GateEvent] = []
    for line in lines[start + 1 :]:
        if line == "END":
            break
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        gate = parts[0]
        qubits = tuple(int(value.removeprefix("q")) for value in parts[1:])
        if any(value < 0 or value >= qubit_count for value in qubits):
            raise ValueError("Feynman returned an out-of-range wire")
        if gate == "swap":
            if len(qubits) != 2:
                raise ValueError("invalid Feynman swap")
            first, second = qubits
            events.extend(
                [
                    GateEvent("cx", (first, second)),
                    GateEvent("cx", (second, first)),
                    GateEvent("cx", (first, second)),
                ]
            )
        elif gate in _OUTPUT_GATES:
            events.append(GateEvent(_OUTPUT_GATES[gate], qubits))
        else:
            raise ValueError(f"Feynman returned unsupported gate {gate!r}")
    else:
        raise ValueError("Feynman output has no END marker")
    return events


def _optimize_worker(
    connection, executable: str, revision: str, timeout: float,
    lowered: LoweredCircuit, action: str,
) -> None:
    try:
        adapter = FeynmanAdapter(executable, revision=revision, timeout_seconds=timeout)
        connection.send(adapter._optimize_direct(lowered, action, timeout_seconds=timeout))
    except BaseException as exc:
        connection.send(AdapterResult("feynman", revision, action, "failed", 0.0, reason=str(exc)))
    finally:
        connection.close()


class FeynmanAdapter:
    def __init__(
        self,
        executable: str | Path = "feynopt",
        *,
        revision: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        resolved = shutil.which(str(executable))
        self.executable = resolved or str(executable)
        self.revision = revision
        self.timeout_seconds = timeout_seconds

    def available_actions(self, *, timeout_seconds: float | None = None) -> set[str]:
        completed = subprocess.run(
            [self.executable, "-h"],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds if timeout_seconds is None else timeout_seconds,
            check=False,
        )
        help_text = completed.stdout + completed.stderr
        return {action for action in FEYNMAN_ACTIONS if f"-{action}" in help_text}

    def optimize(
        self, lowered: LoweredCircuit, action: str, *, timeout_seconds: float | None = None
    ) -> AdapterResult:
        if action not in FEYNMAN_ACTIONS:
            raise ValueError(f"unsupported Feynman action {action!r}")
        if timeout_seconds is None:
            return self._optimize_direct(lowered, action)
        started = time.perf_counter()
        if timeout_seconds <= 0:
            return AdapterResult("feynman", self.revision, action, "timed_out", 0.0, reason="search deadline expired")
        method = "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
        context = multiprocessing.get_context(method)
        reader, writer = context.Pipe(duplex=False)
        process = context.Process(
            target=_optimize_worker,
            args=(writer, self.executable, self.revision, timeout_seconds, lowered, action),
        )
        try:
            process.start()
            writer.close()
            if reader.poll(timeout_seconds):
                try:
                    result = reader.recv()
                except EOFError:
                    result = AdapterResult("feynman", self.revision, action, "failed", 0.0, reason="worker exited without a result")
                process.join(timeout=1)
                return result
            return AdapterResult(
                "feynman", self.revision, action, "timed_out",
                time.perf_counter() - started, reason="Feynman verification exceeded remaining search time",
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

    def _optimize_direct(
        self, lowered: LoweredCircuit, action: str, *, timeout_seconds: float | None = None
    ) -> AdapterResult:
        started = time.perf_counter()
        timeout = self.timeout_seconds if timeout_seconds is None else min(self.timeout_seconds, timeout_seconds)
        qubit_count = lowered.allocated_qubits
        if qubit_count is None:
            qubit_count = lowered.candidate.program.qubit_count + lowered.candidate.workspace_qubits
        try:
            if timeout <= 0:
                raise TimeoutError("search deadline expired")
            if action not in self.available_actions(timeout_seconds=timeout):
                raise ValueError(f"Feynman executable does not advertise -{action}")
            source = events_to_circuit(lowered.events, qubit_count)
            dotqc = _dotqc(lowered, qubit_count)
            with tempfile.TemporaryDirectory(prefix="collective-phase-feynman-") as directory:
                path = Path(directory) / "region.qc"
                path.write_text(dotqc, encoding="ascii")
                completed = subprocess.run(
                    [self.executable, f"-{action}", "-verify", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=max(0.001, timeout - (time.perf_counter() - started)),
                    check=False,
                )
            if completed.returncode != 0:
                raise RuntimeError(
                    completed.stderr.strip()
                    or f"Feynman exited with status {completed.returncode}"
                )
            if "VERIFICATION FAILED" in completed.stdout.upper():
                raise ValueError("Feynman reported failed equivalence verification")
            events = _parse_dotqc(completed.stdout, qubit_count)
            result = events_to_circuit(events, qubit_count)
            phase = equivalence_phase(source, result)
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
                    "backend": "feynman",
                    "revision": self.revision,
                    "action": action,
                    "scope": "whole_circuit",
                    "semantic_boundaries": "invalidated",
                    "clean_scratch_pool": [],
                    "input_event_hash": _event_hash(lowered),
                    "equivalence": "feynman_verify_and_pyzx_full_reduce",
                    "global_phase_correction": -phase,
                },
            )
            optimized.optimization["output_event_hash"] = _event_hash(optimized)
            return AdapterResult(
                "feynman",
                self.revision,
                action,
                "verified",
                time.perf_counter() - started,
                optimized,
            )
        except Exception as exc:
            return AdapterResult(
                "feynman",
                self.revision,
                action,
                "failed",
                time.perf_counter() - started,
                reason=str(exc),
            )
