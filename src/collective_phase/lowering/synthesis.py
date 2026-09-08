from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path

import numpy as np

from ..ir import ScaledAngle


@dataclass(frozen=True)
class RotationSynthesis:
    angle_key: str
    tolerance: float
    gates: tuple[str, ...]
    t_count: int
    clifford_count: int
    actual_operator_error: float
    requested_error: float
    backend: str
    backend_version: str
    circuit_global_phase: float
    exact: bool

    def to_dict(self) -> dict:
        result = asdict(self)
        result["gates"] = list(self.gates)
        return result

    @classmethod
    def from_dict(cls, value: dict) -> "RotationSynthesis":
        value = dict(value)
        value["gates"] = tuple(value["gates"])
        return cls(**value)


class RotationSynthesizer:
    def __init__(self, cache_path: str | Path | None = None, seed: int = 0) -> None:
        self.cache_path = Path(cache_path) if cache_path is not None else None
        self.seed = seed
        self._cache: dict[str, dict] = {}
        if self.cache_path is not None and self.cache_path.exists():
            self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))

    @staticmethod
    def _exact(angle: ScaledAngle, tolerance: float) -> RotationSynthesis:
        assert angle.pi_multiple is not None
        quarter_turns = int(angle.pi_multiple / (angle.pi_multiple.__class__(1, 4))) % 8
        gates = {
            0: (),
            1: ("t",),
            2: ("s",),
            3: ("s", "t"),
            4: ("z",),
            5: ("z", "t"),
            6: ("sdg",),
            7: ("tdg",),
        }[quarter_turns]
        return RotationSynthesis(
            angle_key=angle.cache_key,
            tolerance=tolerance,
            gates=gates,
            t_count=sum(gate in {"t", "tdg"} for gate in gates),
            clifford_count=sum(gate not in {"t", "tdg"} for gate in gates),
            actual_operator_error=0.0,
            requested_error=tolerance,
            backend="exact_special_angle",
            backend_version="1",
            circuit_global_phase=0.0,
            exact=True,
        )

    def synthesize(self, angle: ScaledAngle, tolerance: float) -> RotationSynthesis:
        if not (0 < tolerance < 1):
            raise ValueError("rotation tolerance must lie in (0, 1)")
        if angle.is_exact_clifford_t:
            return self._exact(angle, tolerance)
        key = f"{angle.cache_key}|{tolerance:.17g}|pygridsynth-2.0.0|seed={self.seed}"
        if key in self._cache:
            return RotationSynthesis.from_dict(self._cache[key])
        try:
            import pygridsynth
            from pygridsynth.gridsynth import gridsynth_circuit
            from pygridsynth.quantum_gate import Rz
        except ImportError as exc:
            raise RuntimeError(
                "generic rotation synthesis requires pygridsynth==2.0.0"
            ) from exc

        theta = angle.radians
        circuit = gridsynth_circuit(
            theta=repr(theta), epsilon=repr(tolerance), seed=self.seed
        )
        gate_names = tuple(gate.to_simple_str().lower() for gate in circuit)
        normalized = tuple("tdg" if gate == "t*" else gate for gate in gate_names)
        unknown = set(normalized) - {"h", "t", "tdg", "s", "sdg", "x", "z", "w"}
        if unknown:
            raise RuntimeError(f"pygridsynth returned unsupported gates: {sorted(unknown)}")
        target = np.array(
            [[complex(Rz(theta)[row, column]) for column in range(2)] for row in range(2)]
        )
        actual_matrix = circuit.to_complex_matrix(1)
        actual = np.array(
            [
                [complex(actual_matrix[row, column]) for column in range(2)]
                for row in range(2)
            ]
        )
        actual_error = float(np.linalg.norm(target - actual, ord=2))
        if actual_error > tolerance * (1 + 1e-7):
            raise RuntimeError(
                f"synthesized rotation exceeds tolerance: {actual_error} > {tolerance}"
            )
        result = RotationSynthesis(
            angle_key=angle.cache_key,
            tolerance=tolerance,
            gates=normalized,
            t_count=sum(gate in {"t", "tdg"} for gate in normalized),
            clifford_count=sum(gate not in {"t", "tdg", "w"} for gate in normalized),
            actual_operator_error=actual_error,
            requested_error=tolerance,
            backend="pygridsynth",
            backend_version=getattr(pygridsynth, "__version__", "2.0.0"),
            circuit_global_phase=float(circuit.phase),
            exact=False,
        )
        self._cache[key] = result.to_dict()
        if self.cache_path is not None:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self._cache, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return result

