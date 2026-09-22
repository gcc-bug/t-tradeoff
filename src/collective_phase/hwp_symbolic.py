"""Construction-specific HWP bounds, without complete Clifford+T streams.

Unknown generic rotations contribute zero. Resolved values describe the frozen
unitary implementation, never arbitrary equivalent circuits. Scratch is reserved
through the last inverse operation, regardless of temporary wire idleness.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import time

from .baselines.common import CompilationConstraints, append_direct_term
from .baselines.arithmetic import hamming_weight_schedule
from .baselines.hwp import _emit_adder_batch, compile_hwp_adder_unitary
from .baselines.independent import compile_independent
from .circuit import data_support
from .hwp_pareto import BlockOption, Library, Plan, emit, template_layouts
from .ir import ParityTerm, PhaseBlock, PhaseProgram, ScaledAngle
from .lowering import RotationSynthesizer
from .lowering.lower import lower_candidate_with_rotations
from .lowering.primitives import exact_toffoli_gate_sequence
from .preprocessing import preprocess
from .resources import estimate_resources
from .verification import verify_lowered_circuit


@dataclass(frozen=True)
class TimingTransfer:
    """Max-plus port transfer, None denotes absent dependence."""
    rows: tuple[tuple[int | None, ...], ...]

    @classmethod
    def from_gates(cls, gates, ports):
        rows = [[0 if i == j else None for j in range(ports)] for i in range(ports)]
        for kind, wires in gates:
            increment = int(kind in {"t", "tdg"})
            merged = []
            for j in range(ports):
                values = [rows[q][j] for q in wires if rows[q][j] is not None]
                merged.append(max(values) + increment if values else None)
            for q in wires:
                rows[q] = merged.copy()
        return cls(tuple(tuple(row) for row in rows))

    def apply(self, levels):
        return tuple(max(level + value for level, value in zip(levels, row)
                         if value is not None) for row in self.rows)


TOFFOLI_TIMING = TimingTransfer.from_gates(exact_toffoli_gate_sequence((0, 1, 2)), 3)


def _compressor_transfer(kind, inverse=False):
    logical = ([('cx', (0, 1)), ('cx', (0, 2)), ('toffoli', (1, 2, 3)),
                ('cx', (0, 1)), ('cx', (0, 3)), ('cx', (1, 2))] if kind == 'triple'
               else [('toffoli', (0, 1, 2)), ('cx', (0, 1))])
    gates = []
    for gate, wires in reversed(logical) if inverse else logical:
        gates.extend(exact_toffoli_gate_sequence(wires) if gate == 'toffoli' else [(gate, wires)])
    return TimingTransfer.from_gates(gates, 4 if kind == 'triple' else 3)


COMPRESSOR_TIMING = {(kind, inverse): _compressor_transfer(kind, inverse)
                     for kind in ('triple', 'pair') for inverse in (False, True)}
CX_TIMING = TimingTransfer.from_gates([('cx', (0, 1))], 2)


@dataclass(frozen=True)
class TimingRecipe:
    """Port transfers around phase requests; no Operation objects or local IR."""
    forward: tuple
    phase_ports: tuple[int, ...]
    inverse: tuple
    ports: int

    def depth(self, counts, arrivals=None):
        levels = list(arrivals) if arrivals is not None else [0] * self.ports
        if len(levels) != self.ports or len(counts) != len(self.phase_ports):
            raise ValueError('timing port count mismatch')

        def apply(steps):
            for transfer, wires in steps:
                outputs = transfer.apply(tuple(levels[q] for q in wires))
                for q, value in zip(wires, outputs):
                    levels[q] = value

        apply(self.forward)
        for q, count in zip(self.phase_ports, counts):
            levels[q] += count
        apply(self.inverse)
        return tuple(levels)


def timing_recipe(option):
    """Describe the fixed recipe at compressor granularity, retaining port timing."""
    n, m = len(option.data_wires), len(option.local_masks)
    if option.layout == 'direct':
        support = data_support(option.local_masks[0])
        steps = tuple((CX_TIMING, (q, support[0])) for q in support[1:])
        return TimingRecipe(steps, (support[0],), tuple(reversed(steps)), n)
    if option.layout == 'copied_parities':
        inputs = tuple(range(n, n + m))
        prep = tuple((CX_TIMING, (q, target)) for mask, target in zip(option.local_masks, inputs)
                     for q in data_support(mask))
        # The emitter reverses predicate order, but keeps each parity's CNOT order.
        cleanup = tuple((CX_TIMING, (q, target)) for mask, target in
                        reversed(tuple(zip(option.local_masks, inputs))) for q in data_support(mask))
        start = n + m
    else:
        inputs = tuple(mask.bit_length() - 1 for mask in option.local_masks)
        prep = cleanup = ()
        start = n
    carries = tuple(range(start, n + option.workspace))
    steps, layout = hamming_weight_schedule(inputs, carries, ordering=option.ordering)
    forward = prep + tuple((COMPRESSOR_TIMING[kind, False], wires) for kind, wires in steps)
    inverse = tuple((COMPRESSOR_TIMING[kind, True], wires) for kind, wires in reversed(steps)) + cleanup
    return TimingRecipe(forward, layout.output_qubits, inverse, n + option.workspace)


@dataclass(frozen=True)
class RotationRequest:
    angle: ScaledAngle
    multiplier: int
    tolerance: float
    key: str
    # One request per weight-bit occurrence; shared keys do not erase multiplicity.


@dataclass(frozen=True)
class SymbolicOption:
    id: int
    terms: int
    group: int
    boundary: int
    footprint: int
    data_wires: tuple[int, ...]
    local_masks: tuple[int, ...]
    angle_id: str
    coefficient: int
    layout: str
    ordering: str
    allowance: float
    workspace: int
    arithmetic_t: int
    requests: tuple[RotationRequest, ...]
    template_key: tuple


@dataclass(frozen=True)
class ResourceEvidence:
    lower: tuple[int, int, int]
    upper: tuple[int, int, int] | None
    exact: bool


@dataclass(frozen=True)
class ComputationGraph:
    operations: tuple
    # (role, physical wires, allocation start, release boundary).
    lifetimes: tuple
    retained_garbage: tuple[int, ...]


class SymbolicLibrary:
    def __init__(self, program, total_error, synthesizer, *, max_batch=10,
                 max_terms=10, orderings=("staged",), evaluator="transfer"):
        started = time.perf_counter()
        if not math.isfinite(total_error) or not 0 < total_error < 1:
            raise ValueError("total_error must lie in (0, 1)")
        if max_batch < 1 or max_terms < 1:
            raise ValueError("positive size limits required")
        if evaluator not in {"transfer", "graph"}:
            raise ValueError("unknown symbolic evaluator")
        self.evaluator = evaluator
        self.recipes = {}
        if not orderings or len(set(orderings)) != len(orderings) or any(
                x not in {"staged", "readiness"} for x in orderings):
            raise ValueError("invalid arithmetic orderings")
        normalized = preprocess(program)
        if len(normalized.terms) > max_terms or program.qubit_count > 10:
            raise ValueError("instance exceeds the declared exact-search/verification cap")
        boundaries = {block.id: i for i, block in enumerate(program.blocks)}
        if len(boundaries) != len(program.blocks):
            raise ValueError("block IDs must be unique")
        self.program, self.terms = program, normalized.terms
        self.total_error, self.max_batch = total_error, max_batch
        self.synthesizer = synthesizer
        indices = {term.id: i for i, term in enumerate(self.terms)}
        self.groups = tuple(tuple(indices[t.id] for t in g.terms) for g in normalized.groups)
        self.options = []
        self.rotations, self.graphs, self.summaries, self.materialized = {}, {}, {}, {}
        self.epoch = 0
        self.stats = dict(descriptors=0, graphs=0, primitive_summaries=1,
                          timing_recipes=0, evaluations=0, evaluator=evaluator,
                          rotation_keys=0, rotations_refined=0, templates_materialized=0,
                          circuits_emitted=0, circuits_verified=0, description_seconds=0.,
                          graph_seconds=0., summary_seconds=0., synthesis_seconds=0.,
                          lowering_seconds=0., verification_seconds=0.)
        for group_id, group in enumerate(normalized.groups):
            for size in range(1, min(max_batch, len(group.terms)) + 1):
                for subset in combinations(group.terms, size):
                    footprint = 0
                    for term in subset:
                        footprint |= term.mask
                    wires = tuple(data_support(footprint))
                    masks = tuple(sum(((t.mask >> q) & 1) << i for i, q in enumerate(wires))
                                  for t in subset)
                    allowance = total_error * size / max(1, len(self.terms))
                    for layout in template_layouts(masks, group.coefficient):
                        for ordering in (("staged",) if size == 1 else orderings):
                            multipliers = tuple(group.coefficient * (1 << k)
                                                for k in range(1 if size == 1 else size.bit_length()))
                            angles = tuple(program.angle_map[group.angle_id].scaled(k) for k in multipliers)
                            tolerance = allowance / max(1, sum(not a.is_exact_clifford_t for a in angles))
                            requests = tuple(RotationRequest(a, k, tolerance,
                                f"{a.cache_key}|{tolerance:.17g}|pygridsynth-2.0.0|seed={synthesizer.seed}")
                                for a, k in zip(angles, multipliers))
                            for request in requests:
                                if request.angle.is_exact_clifford_t:
                                    self.rotations[request.key] = synthesizer._exact(request.angle, tolerance)
                            carries = size - size.bit_count() if size > 1 else 0
                            workspace = carries + (size if layout == "copied_parities" else 0)
                            key = (masks, group.angle_id, group.coefficient, layout, ordering,
                                   tuple(r.key for r in requests))
                            self.options.append(SymbolicOption(len(self.options),
                                sum(1 << indices[t.id] for t in subset), group_id,
                                boundaries[group.block_id], footprint, wires, masks,
                                group.angle_id, group.coefficient, layout, ordering, allowance,
                                workspace, 14*carries, requests, key))
        self.options = tuple(self.options)
        self.stats.update(descriptors=len(self.options),
                          rotation_keys=len({r.key for o in self.options for r in o.requests}),
                          description_seconds=time.perf_counter()-started)

    @property
    def full_mask(self):
        return (1 << len(self.terms)) - 1

    def fingerprint(self, ancilla_max, depth_max):
        root = Path(__file__).parent
        evidence = [self.program.to_dict(), self.total_error, self.max_batch,
                    self.synthesizer.seed, [o.template_key for o in self.options],
                    ancilla_max, depth_max, "normalized_term_blocks_v1;unitary;complete-waves",
                    {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(root.rglob("*.py"))}]
        return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()

    def local_program(self, option):
        return PhaseProgram("hwp-template", len(option.data_wires), self.program.angles,
            (PhaseBlock("block", tuple(ParityTerm(f"p{i}", mask, option.angle_id,
                coefficient=option.coefficient) for i, mask in enumerate(option.local_masks))),))

    def graph(self, option):
        key = option.template_key
        if key not in self.graphs:
            started = time.perf_counter()
            local = self.local_program(option)
            group = preprocess(local).groups[0]
            if option.layout == "direct":
                operations = []
                append_direct_term(operations, group.terms[0])
                trace = {}
            else:
                operations, workspace, trace = _emit_adder_batch(local, group, list(group.terms),
                    layout=option.layout, ordering=option.ordering)
                assert workspace == option.workspace
            end = len(operations)
            lifetimes = tuple((role, tuple(trace.get(field, ())), 0, end)
                              for role, field in (("carries", "carry_qubits"),
                                  ("parity_storage", "parity_qubits"))
                              if role != "parity_storage" or option.layout == "copied_parities")
            self.graphs[key] = ComputationGraph(tuple(operations), lifetimes,
                                                tuple(trace.get("retained_garbage_qubits", ())))
            self.stats["graphs"] += 1
            self.stats["graph_seconds"] += time.perf_counter()-started
        return self.graphs[key]

    def evaluate(self, option):
        self.stats['evaluations'] += 1
        counts = tuple(self.rotations[r.key].t_count if r.key in self.rotations else 0
                       for r in option.requests)
        exact = all(r.key in self.rotations for r in option.requests)
        key = (option.template_key, counts, exact)
        if key not in self.summaries:
            started = time.perf_counter()
            depth = (self.graph_depth(option, counts) if self.evaluator == 'graph'
                     else max(self.recipe(option).depth(counts), default=0))
            resources = (option.arithmetic_t + sum(counts), depth, option.workspace)
            self.summaries[key] = ResourceEvidence(resources, resources if exact else None, exact)
            self.stats["summary_seconds"] += time.perf_counter()-started
        return self.summaries[key]

    def recipe(self, option):
        # Timing topology is independent of angle, precision and physical embedding.
        key = option.local_masks, option.layout, option.ordering
        if key not in self.recipes:
            self.recipes[key] = timing_recipe(option)
            self.stats['timing_recipes'] += 1
        return self.recipes[key]

    def graph_depth(self, option, counts):
        graph = self.graph(option)
        levels = [0] * (len(option.data_wires) + option.workspace)
        rotations = iter(counts)
        for op in graph.operations:
            if op.kind == "phase":
                levels[op.qubits[0]] += next(rotations)
            elif op.kind == "toffoli":
                out = TOFFOLI_TIMING.apply(tuple(levels[q] for q in op.qubits))
                for q, value in zip(op.qubits, out):
                    levels[q] = value
            elif op.kind in {"cx", "x"}:
                value = max(levels[q] for q in op.qubits)
                for q in op.qubits:
                    levels[q] = value
            else:
                raise ValueError(f"unsupported symbolic primitive {op.kind}")
        return max(levels, default=0)

    def unresolved(self, option):
        return tuple(r for r in option.requests if r.key not in self.rotations)

    def refine(self, request, check_time=lambda: None):
        check_time()
        if request.key not in self.rotations:
            started = time.perf_counter()
            result = self.synthesizer.synthesize(request.angle, request.tolerance)
            self.stats["synthesis_seconds"] += time.perf_counter()-started
            self.rotations[request.key] = result
            self.stats["rotations_refined"] += 1
            self.epoch += 1
        # The backend call is atomic; a deadline may overrun by one synthesis.
        check_time()

    def resolve(self, option, check_time=lambda: None):
        for request in self.unresolved(option):
            self.refine(request, check_time)
        return self.evaluate(option)

    def materialize(self, option, check_time=lambda: None):
        self.resolve(option, check_time)
        key = option.template_key
        if key not in self.materialized:
            check_time()
            started = time.perf_counter()
            local = self.local_program(option)
            constraints = CompilationConstraints(None, "unitary_clifford_t", hwp_search_cap=self.max_batch)
            candidate = (compile_independent(local, constraints) if option.layout == "direct" else
                         compile_hwp_adder_unitary(local, constraints, batch_limit=len(option.local_masks),
                                                 layout=option.layout, ordering=option.ordering))
            lowered = lower_candidate_with_rotations(candidate, option.allowance,
                [self.rotations[r.key] for r in option.requests], [])
            self.stats["lowering_seconds"] += time.perf_counter()-started
            self.stats["templates_materialized"] += 1
            started = time.perf_counter()
            proof = verify_lowered_circuit(lowered, option.allowance, memory_cap_bytes=1)
            self.stats["verification_seconds"] += time.perf_counter()-started
            if not proof.status.startswith("verified_lowered_"):
                raise ValueError(f"symbolic template verification failed: {proof.message}")
            counts = tuple(self.rotations[r.key].t_count for r in option.requests)
            if self.graph_depth(option, counts) != self.evaluate(option).lower[1]:
                raise ValueError("transfer disagrees with high-level graph")
            r = estimate_resources(lowered)
            if (r.t_count, r.t_depth, r.peak_workspace) != self.evaluate(option).lower:
                raise ValueError("symbolic prediction disagrees with emitted template")
            self.materialized[key] = lowered
            check_time()
        return self.materialized[key]

    def plan_resources(self, waves):
        t = d = a = 0
        for wave in waves:
            rs = [self.evaluate(self.options[i]).lower for i in wave]
            t += sum(r[0] for r in rs)
            d += max(r[1] for r in rs)
            a = max(a, sum(r[2] for r in rs))
        return t, d, a

    def emit(self, plan, *, check_time=lambda: None, memory_cap_bytes=1):
        options = [None] * len(self.options)
        for i in {i for wave in plan.waves for i in wave}:
            o = self.options[i]
            lowered = self.materialize(o, check_time)
            options[i] = BlockOption(o.id, o.terms, o.group, o.boundary, o.footprint,
                o.data_wires, o.layout, self.evaluate(o).lower, lowered, o.allowance, o.ordering)
        check_time()
        library = Library(self.program, self.terms, self.groups, tuple(options),
                          self.total_error, self.max_batch, {})
        # emit includes final lowering, resource checks, and verification.
        timings = {}
        result = emit(library, plan, memory_cap_bytes=memory_cap_bytes, timings=timings)
        for phase, seconds in timings.items():
            self.stats[phase] += seconds
        self.stats["circuits_emitted"] += 1
        self.stats["circuits_verified"] += 1
        return result
