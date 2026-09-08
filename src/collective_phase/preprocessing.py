from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .ir import PhaseProgram


PREPROCESSING_VERSION = "canonical-v2"


@dataclass(frozen=True)
class NormalizedTerm:
    id: str
    block_id: str
    mask: int
    angle_id: str
    coefficient: int
    source_term_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source_term_ids"] = list(self.source_term_ids)
        return value


@dataclass(frozen=True)
class CompatibleGroup:
    id: str
    block_id: str
    angle_id: str
    coefficient: int
    terms: tuple[NormalizedTerm, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "block_id": self.block_id,
            "angle_id": self.angle_id,
            "coefficient": self.coefficient,
            "terms": [term.to_dict() for term in self.terms],
        }


@dataclass(frozen=True)
class PreprocessedProgram:
    version: str
    terms: tuple[NormalizedTerm, ...]
    groups: tuple[CompatibleGroup, ...]
    global_phase: float
    trace: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "terms": [term.to_dict() for term in self.terms],
            "groups": [group.to_dict() for group in self.groups],
            "global_phase": self.global_phase,
            "trace": list(self.trace),
        }

    def phase_radians(self, program: PhaseProgram, x: int) -> float:
        result = self.global_phase
        for term in self.terms:
            parity = (term.mask & x).bit_count() & 1
            result += (
                program.angle_map[term.angle_id].radians
                * term.coefficient
                * parity
            )
        return result


def preprocess(program: PhaseProgram) -> PreprocessedProgram:
    """Create the one canonical, block-local normalized representation."""
    normalized: list[NormalizedTerm] = []
    trace: list[dict[str, Any]] = []
    global_phase = 0.0

    for block_index, block in enumerate(program.blocks):
        accumulators: dict[tuple[int, str], int] = {}
        provenance: dict[tuple[int, str], list[str]] = {}
        for term in block.terms:
            coefficient = term.coefficient
            if term.mask == 0:
                if term.offset:
                    global_phase += (
                        program.angle_map[term.angle_id].radians * coefficient
                    )
                trace.append(
                    {
                        "action": "constant_eliminated",
                        "block_id": block.id,
                        "source_term_ids": [term.id],
                        "constant_multiplier": coefficient if term.offset else 0,
                        "angle_id": term.angle_id,
                    }
                )
                continue
            if term.offset:
                global_phase += program.angle_map[term.angle_id].radians * coefficient
                coefficient = -coefficient
                trace.append(
                    {
                        "action": "affine_complement_normalized",
                        "block_id": block.id,
                        "source_term_ids": [term.id],
                        "constant_multiplier": term.coefficient,
                        "normalized_coefficient": coefficient,
                        "angle_id": term.angle_id,
                    }
                )
            key = (term.mask, term.angle_id)
            accumulators[key] = accumulators.get(key, 0) + coefficient
            provenance.setdefault(key, []).append(term.id)

        for term_index, ((mask, angle_id), coefficient) in enumerate(
            sorted(accumulators.items())
        ):
            source_ids = tuple(provenance[(mask, angle_id)])
            if coefficient == 0:
                trace.append(
                    {
                        "action": "duplicate_cancellation",
                        "block_id": block.id,
                        "source_term_ids": list(source_ids),
                        "mask": mask,
                        "angle_id": angle_id,
                    }
                )
                continue
            action = "duplicate_merged" if len(source_ids) > 1 else "term_preserved"
            normalized_term = NormalizedTerm(
                id=f"normalized:{block_index}:{term_index}",
                block_id=block.id,
                mask=mask,
                angle_id=angle_id,
                coefficient=coefficient,
                source_term_ids=source_ids,
            )
            normalized.append(normalized_term)
            trace.append(
                {
                    "action": action,
                    "block_id": block.id,
                    "source_term_ids": list(source_ids),
                    "normalized_term_id": normalized_term.id,
                    "mask": mask,
                    "angle_id": angle_id,
                    "coefficient": coefficient,
                }
            )

    grouped: dict[tuple[str, str, int], list[NormalizedTerm]] = {}
    group_order: list[tuple[str, str, int]] = []
    for term in normalized:
        key = (term.block_id, term.angle_id, term.coefficient)
        if key not in grouped:
            grouped[key] = []
            group_order.append(key)
        grouped[key].append(term)
    groups = tuple(
        CompatibleGroup(
            id=f"group:{index}",
            block_id=key[0],
            angle_id=key[1],
            coefficient=key[2],
            terms=tuple(grouped[key]),
        )
        for index, key in enumerate(group_order)
    )
    trace.append(
        {
            "action": "compatible_groups_formed",
            "preprocessing_version": PREPROCESSING_VERSION,
            "group_ids": [group.id for group in groups],
        }
    )
    return PreprocessedProgram(
        version=PREPROCESSING_VERSION,
        terms=tuple(normalized),
        groups=groups,
        global_phase=global_phase,
        trace=tuple(trace),
    )

