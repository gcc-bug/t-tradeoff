from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from ..circuit import Operation, data_support
from ..ir import PhaseProgram
from ..preprocessing import NormalizedTerm


SUPPORTED_MODELS = {
    "unitary_clifford_t",
    "measurement_assisted_clifford_t",
}


@dataclass(frozen=True)
class CompilationConstraints:
    workspace_budget: int | None
    model_profile: str
    batch_policy: str = "balanced"
    objective: str = "t_count"
    hwp_search_cap: int = 8

    def __post_init__(self) -> None:
        if self.workspace_budget is not None and self.workspace_budget < 0:
            raise ValueError("workspace budget must be non-negative")
        if self.model_profile not in SUPPORTED_MODELS:
            raise ValueError(f"unsupported model profile {self.model_profile!r}")
        if self.batch_policy not in {"balanced", "cost_aware"}:
            raise ValueError(f"unsupported batch policy {self.batch_policy!r}")
        if self.objective not in {"t_count", "t_depth", "ancilla", "balance"}:
            raise ValueError(f"unsupported objective {self.objective!r}")
        if self.hwp_search_cap < 1:
            raise ValueError("hwp search cap must be positive")


def append_parity_phase(
    operations: list[Operation], mask: int, angle_id: str, multiplier: int
) -> None:
    support = data_support(mask)
    if not support:
        raise ValueError("constant phases must be handled before parity emission")
    target = support[0]
    controls = support[1:]
    operations.extend(Operation("cx", (control, target)) for control in controls)
    operations.append(Operation("phase", (target,), angle_id, multiplier))
    operations.extend(Operation("cx", (control, target)) for control in reversed(controls))


def append_parity_into(
    operations: list[Operation], mask: int, target: int
) -> None:
    operations.extend(
        Operation("cx", (control, target)) for control in data_support(mask)
    )


def append_direct_term(
    operations: list[Operation], term: NormalizedTerm
) -> None:
    append_parity_phase(
        operations, term.mask, term.angle_id, term.coefficient
    )


def validate_equal_unit_terms(program: PhaseProgram) -> str | None:
    if any(term.offset for term in program.terms):
        return "HWP currently supports only linear predicates (offset=false)"
    if any(term.coefficient != 1 for term in program.terms):
        return "HWP requires equal positive unit coefficients"
    for block in program.blocks:
        if len({term.angle_id for term in block.terms}) > 1:
            return "each HWP block must contain one exact angle class"
    return None


def hwp_workspace(batch_size: int) -> int:
    if batch_size <= 0:
        return 0
    if batch_size == 1:
        return 1
    # Conservative: predicates stay materialized and the weight output is
    # separate. The k-1 bound covers the adder scratch except at k=2, where
    # two explicit output bits are needed by this semantic representation.
    return batch_size + max(batch_size - 1, batch_size.bit_length())


def max_batch_size(term_count: int, budget: int | None, workspace_fn) -> int:
    if term_count == 0:
        return 0
    if budget is None:
        return term_count
    result = 0
    for size in range(1, term_count + 1):
        if workspace_fn(size) <= budget:
            result = size
    return result


def _surrogate_cost(size: int) -> int:
    if size == 1:
        return 40
    hwp_adders = size - size.bit_count()
    return 4 * hwp_adders + size.bit_length() * 40


def batch_sizes(
    term_count: int,
    capacity: int,
    policy: str,
) -> list[int]:
    if term_count == 0:
        return []
    if capacity < 1:
        raise ValueError("batch capacity must be positive")
    if policy == "balanced":
        batch_count = math.ceil(term_count / capacity)
        base, extra = divmod(term_count, batch_count)
        return [base + 1] * extra + [base] * (batch_count - extra)
    costs = [0] + [10**18] * term_count
    previous = [0] * (term_count + 1)
    for total in range(1, term_count + 1):
        for size in range(1, min(capacity, total) + 1):
            cost = costs[total - size] + _surrogate_cost(size)
            if cost < costs[total]:
                costs[total] = cost
                previous[total] = size
    result: list[int] = []
    remaining = term_count
    while remaining:
        result.append(previous[remaining])
        remaining -= previous[remaining]
    return result


def chunks(items: list, sizes: Iterable[int]) -> list[list]:
    output: list[list] = []
    position = 0
    for size in sizes:
        output.append(items[position : position + size])
        position += size
    if position != len(items):
        raise AssertionError("batch sizes do not cover input")
    return output
