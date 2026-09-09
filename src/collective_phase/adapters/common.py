from __future__ import annotations

from dataclasses import dataclass

from ..lowering import LoweredCircuit


@dataclass(frozen=True)
class AdapterResult:
    backend: str
    revision: str
    action: str
    status: str
    backend_seconds: float
    lowered: LoweredCircuit | None = None
    reason: str | None = None

    @property
    def verified(self) -> bool:
        return self.status == "verified" and self.lowered is not None
