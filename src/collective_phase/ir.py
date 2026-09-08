from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
import math
import re
from typing import Any, Iterable


_PI_RE = re.compile(
    r"^(?P<sign>[+-]?)(?:(?P<num>\d+)\*)?pi(?:/(?P<den>\d+))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ScaledAngle:
    """An integer multiple of a declared angle, without fuzzy class merging."""

    binding_id: str
    expression: str
    multiplier: int
    pi_multiple: Fraction | None
    decimal_value: Decimal | None

    @property
    def radians(self) -> float:
        if self.pi_multiple is not None:
            return float(self.pi_multiple) * math.pi
        assert self.decimal_value is not None
        return float(self.decimal_value)

    @property
    def cache_key(self) -> str:
        if self.pi_multiple is not None:
            return f"pi*{self.pi_multiple.numerator}/{self.pi_multiple.denominator}"
        assert self.decimal_value is not None
        return format(self.decimal_value, "f")

    @property
    def is_exact_clifford_t(self) -> bool:
        return self.pi_multiple is not None and (
            self.pi_multiple / Fraction(1, 4)
        ).denominator == 1


@dataclass(frozen=True)
class AngleBinding:
    """A named numeric binding. Equality is the ID, not float proximity."""

    id: str
    expression: str
    _pi_multiple: Fraction | None = field(init=False, repr=False)
    _decimal_value: Decimal | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expression = str(self.expression).strip().replace(" ", "")
        if not self.id:
            raise ValueError("angle binding ID must be non-empty")
        match = _PI_RE.fullmatch(expression)
        if match:
            sign = -1 if match.group("sign") == "-" else 1
            numerator = int(match.group("num") or "1")
            denominator = int(match.group("den") or "1")
            if denominator == 0:
                raise ValueError("angle denominator cannot be zero")
            object.__setattr__(self, "_pi_multiple", Fraction(sign * numerator, denominator))
            object.__setattr__(self, "_decimal_value", None)
        else:
            try:
                value = Decimal(expression)
            except Exception as exc:
                raise ValueError(f"unsupported angle expression: {self.expression!r}") from exc
            if not value.is_finite():
                raise ValueError("angle must be finite")
            object.__setattr__(self, "_pi_multiple", None)
            object.__setattr__(self, "_decimal_value", value)
        object.__setattr__(self, "expression", expression)

    def scaled(self, multiplier: int) -> ScaledAngle:
        if not isinstance(multiplier, int):
            raise TypeError("angle multiplier must be an integer")
        return ScaledAngle(
            binding_id=self.id,
            expression=self.expression,
            multiplier=multiplier,
            pi_multiple=(
                self._pi_multiple * multiplier
                if self._pi_multiple is not None
                else None
            ),
            decimal_value=(
                self._decimal_value * multiplier
                if self._decimal_value is not None
                else None
            ),
        )

    @property
    def radians(self) -> float:
        return self.scaled(1).radians

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "value": self.expression}


@dataclass(frozen=True)
class ParityTerm:
    id: str
    mask: int
    angle_id: str
    offset: bool = False
    coefficient: int = 1
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)

    def evaluate(self, x: int) -> int:
        return ((self.mask & x).bit_count() & 1) ^ int(self.offset)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mask": self.mask,
            "offset": self.offset,
            "coefficient": self.coefficient,
            "angle_id": self.angle_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PhaseBlock:
    id: str
    terms: tuple[ParityTerm, ...]
    boundary: str = "diagonal"
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "boundary": self.boundary,
            "terms": [term.to_dict() for term in self.terms],
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PhaseProgram:
    id: str
    qubit_count: int
    angles: tuple[AngleBinding, ...]
    blocks: tuple[PhaseBlock, ...]
    qubit_order: str = "little_endian_mask_bit_i_is_qubit_i"
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.qubit_count < 0:
            raise ValueError("qubit_count must be non-negative")
        angle_ids = [angle.id for angle in self.angles]
        if len(set(angle_ids)) != len(angle_ids):
            raise ValueError("angle binding IDs must be unique")
        known_angles = set(angle_ids)
        term_ids: set[str] = set()
        for block in self.blocks:
            if block.boundary != "diagonal":
                raise ValueError(f"unsupported block boundary {block.boundary!r}")
            for term in block.terms:
                if term.id in term_ids:
                    raise ValueError(f"duplicate term ID {term.id!r}")
                term_ids.add(term.id)
                if term.mask < 0 or term.mask >= (1 << self.qubit_count):
                    raise ValueError(f"term {term.id!r} mask exceeds declared qubits")
                if term.angle_id not in known_angles:
                    raise ValueError(f"term {term.id!r} references unknown angle")
                if not isinstance(term.coefficient, int):
                    raise TypeError("term coefficients must be exact integers")

    @property
    def angle_map(self) -> dict[str, AngleBinding]:
        return {angle.id: angle for angle in self.angles}

    @property
    def terms(self) -> tuple[ParityTerm, ...]:
        return tuple(term for block in self.blocks for term in block.terms)

    def integer_values(self, x: int) -> dict[str, int]:
        if x < 0 or x >= (1 << self.qubit_count):
            raise ValueError("basis input is outside the data register")
        values = {angle.id: 0 for angle in self.angles}
        for term in self.terms:
            values[term.angle_id] += term.coefficient * term.evaluate(x)
        return values

    def phase_radians(self, x: int) -> float:
        values = self.integer_values(x)
        return sum(self.angle_map[key].radians * value for key, value in values.items())

    def normalized_groups(self) -> tuple[dict[tuple[int, str], int], float, list[dict[str, Any]]]:
        """Normalize affine predicates into linear predicates plus global phase."""
        groups: dict[tuple[int, str], int] = {}
        global_phase = 0.0
        trace: list[dict[str, Any]] = []
        for term in self.terms:
            coefficient = term.coefficient
            if term.mask == 0:
                if term.offset:
                    global_phase += self.angle_map[term.angle_id].radians * coefficient
                trace.append({"term": term.id, "action": "constant_eliminated"})
                continue
            if term.offset:
                global_phase += self.angle_map[term.angle_id].radians * coefficient
                coefficient = -coefficient
                trace.append({"term": term.id, "action": "affine_complement_normalized"})
            key = (term.mask, term.angle_id)
            groups[key] = groups.get(key, 0) + coefficient
        groups = {key: value for key, value in groups.items() if value != 0}
        return groups, global_phase, trace

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.id,
            "qubit_count": self.qubit_count,
            "qubit_order": self.qubit_order,
            "angles": [angle.to_dict() for angle in self.angles],
            "blocks": [block.to_dict() for block in self.blocks],
            "metadata": self.metadata,
        }


def make_program(
    case_id: str,
    qubit_count: int,
    masks: Iterable[int],
    angle: AngleBinding,
    *,
    coefficients: Iterable[int] | None = None,
    metadata: dict[str, Any] | None = None,
) -> PhaseProgram:
    mask_list = list(masks)
    coeff_list = list(coefficients) if coefficients is not None else [1] * len(mask_list)
    if len(mask_list) != len(coeff_list):
        raise ValueError("mask and coefficient lengths differ")
    terms = tuple(
        ParityTerm(
            id=f"{case_id}:term:{index}",
            mask=mask,
            angle_id=angle.id,
            coefficient=coefficient,
        )
        for index, (mask, coefficient) in enumerate(zip(mask_list, coeff_list, strict=True))
    )
    return PhaseProgram(
        id=case_id,
        qubit_count=qubit_count,
        angles=(angle,),
        blocks=(PhaseBlock(id=f"{case_id}:block:0", terms=terms),),
        metadata=metadata or {},
    )

