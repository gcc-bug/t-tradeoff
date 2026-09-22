# Symbolic HWP bounds

Implementation base: `b68153e12aad4c11563159dac39821ab5f3dc3ec`.
Branch: `research/hwp-symbolic-bounds`. The handoff is
[`t-tradeoff-symbolic-bounds-plan.md`](../t-tradeoff-symbolic-bounds-plan.md).
The implementation follows its four stages: descriptors and timing summaries;
bound-guided search; one optional arithmetic ordering; frozen H1/H2 comparison.

## Contract and implementation

`SymbolicLibrary` in `src/collective_phase/hwp_symbolic.py` enumerates immutable
subset recipes with coverage, original boundary, compact-wire mapping, layout,
arithmetic ordering, angle multipliers, exact tolerance keys, workspace, and
arithmetic T count. This stage creates neither a `Candidate` nor a gate stream
nor a generic synthesis result. Applicability uses the eager library's shared
`template_layouts` helper on normalized templates. This deliberately preserves
the library's normalization semantics, including canonicalizing complemented
inputs and repeated predicates before describing local templates.

`graph(option)` calls the existing high-level arithmetic/parity builder and
stores logical operations with rotation placeholders. Graphs are shared only
when their full predicate structures, orderings, and synthesis contracts agree.
Graph construction and summary evaluation are charged separately. Workspace
lifetimes reserve parity storage and carries until block cleanup ends; retained
garbage is recorded. Allocation is exact, and there is no mid-block reuse.
Allocated clean scratch, occupied information, and reusable zeroed scratch are
not interchangeable: this milestone reserves the entire declared allocation
while a block executes, and only the clean block boundary permits reuse.

`evaluate(option)` returns `ResourceEvidence(lower, upper, exact)`. Unknown
rotation upper bounds are `None`. Their T count and depth lower bounds are zero;
no empirical estimate enters a certificate. Exact special angles use the existing
exact path. Generic results are synthesized and checked once per actual angle,
tolerance, backend/version, and seed key, but are charged at every occurrence.
Allowances are `epsilon*m/N`, divided by the number of generic rotations only.

The seven-T Toffoli template is compiled once into a max-plus port transfer.
CNOTs synchronize the actual wires even though they have zero T weight. A phase
advances its target by its synthesized T count. Composition over the recorded
forward/phase/inverse operations reproduces `schedule_events`, including unequal
input arrival times. Replacing unresolved rotations by zero is monotone, so the
result is a lower bound on this implementation. A scalar Toffoli depth would not
provide the same guarantee.

`materialize` invokes the existing compiler only for selected templates, reuses
resolved rotations, verifies the template, and checks all three resource values.
`emit` composes selected templates using the existing plan/circuit schemas and
verifies the whole finalist. A mismatch or verification failure raises an error.
It cannot establish infeasibility. Unresolved options are never represented as
`LoweredCircuit` objects.

## Search guarantees

`symbolic_search` in `hwp_cost_search.py` uses the existing rational objectives,
`Plan`, `SearchResult`, limits, and fractional per-term completion bound. It first
tries a direct verified seed; a failed depth constraint only rejects that seed.
It searches all eligible descriptors, refining selected-prefix rotations in
shared-use order. That order is heuristic; bounds are not. Resolved costs can
change the priority of already queued nodes; old priorities remain conservative.
No uncertain-resource dominance is performed. Exact prefix labels may dominate
only at the same remaining-term state.

Waves are generated recursively and streamed instead of accumulated into a full
within-cover Pareto table. For chosen wave resources `(Tw,Dw,Aw)`, prefix
`(Tp,Dp,Ap)`, and a relaxed bound `(Tr,Dr,Ar)` for all still-uncovered terms, the
partial-family resource bound is

```
(Tp + Tw + Tr, Dp + max(Dw, Dr), max(Ap, Aw, Ar)).
```

The maximum in depth is necessary because remaining blocks may join the open
wave. Only after the wave closes does future depth add sequentially. Workspace
adds within the chosen wave and takes a maximum across waves. The relaxation
may ignore conflicts and alternative packing, which weakens but does not raise
the bound. The active parent's bound remains pending until generation completes.
Deadline checks occur inside recursion and option scans. The same pending rule
covers interrupted rotation refinement and pre-emission work.

Only a successfully emitted and verified plan becomes `U`. The minimum of queued
keys, the pending-family bound, and `U` is `L`. Atomic synthesis and verification
calls may finish after a deadline; their work is charged. A timeout before any
verified plan returns `TIMEOUT`, `U=None`, and a sound lower bound. A normalized
empty input is emitted and verified as the zero-resource plan. A gap of zero is
exact only for the finite family, precision, clean-ancilla unitary primitives,
and complete-wave model. Ordinary scheduled depth is separately reported.

Fingerprints bind the program, full recipe/precision keys, ordering variants,
seed, caps, and implementation source hashes. Old eager archive certificates
are not imported into symbolic search. The eager DP and its original wave
generator remain available as an independent reference path.

## Optional arithmetic ordering

The original staged ordering is still the default. `ordering='readiness'` sorts
active equal-weight bits by `(estimated readiness, wire ID)`, compresses the first
three, returns the sum to the current bucket, and sends the new carry to the next
weight. Readiness uses logical Toffoli weight one and CNOT synchronization, solely
as a construction heuristic. A final pair uses the existing half adder. The
precise symbolic evaluator then measures the resulting graph. All retired wires
remain allocated; cleanup reverses the exact recorded operations.

For a bucket with `m` active bits, triple-first reduction and the final pair create
`floor(m/2)` carries and one output. Consequently the total carry count is

```
c(m) = floor(m/2) + c(floor(m/2))
     = sum(k>=1, floor(m/2**k)) = m - popcount(m).
```

Both orderings therefore use `14*c(m)` arithmetic T gates, `bit_length(m)` phase
requests, and `c(m)` native or `m+c(m)` copied scratch for `m>=2`. Singleton direct
options allocate zero scratch. Ordering may change depth, but not these counts.
The eager library and the strong uniform/per-group batching baselines can include
both orderings; the variant is not exclusive to symbolic search. This is an
application of established compressor scheduling, not a global arithmetic optimum
or an unsupported novelty claim.

## Use and validation

```python
from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.hwp_cost_search import symbolic_search
from collective_phase.lowering import RotationSynthesizer

library = SymbolicLibrary(program, 1e-4, RotationSynthesizer(seed=0),
                          max_batch=8, orderings=('staged', 'readiness'))
result = symbolic_search(library, ('1', '0', '0'), 3, 200,
                         timeout_seconds=10)
# result.plan is already verified when present; retain L/U on timeout.
```

The two new focused modules test descriptors and tolerances, shared refinement,
counts/allocation, timing ports against actual gate scheduling, graph/emission
agreement, dense generic-angle finalists for both layouts/orderings, and cache
identity. Search bounds are checked at every tiny remaining-term state and
multiple refinement orders against the existing independently enumerated
partition/wave oracle. Exact optima include depth-only and workspace-only
objectives, tight limits, and both pruning modes. Deterministic interruptions
exercise refinement, recursive wave generation, and materialization. Arithmetic
truth tables and inverse restoration cover all inputs through size ten. The
original constrained `(284,166,3)` witness and its unsupported-point interpretation
are preserved.

```sh
.venv/bin/python -m pytest tests/test_hwp_arithmetic.py tests/test_hwp_pareto.py \
  tests/test_hwp_cost_search.py tests/test_lowering_resources.py \
  tests/test_lowered_verification.py tests/test_preprocessing.py \
  tests/test_hwp_symbolic.py tests/test_hwp_symbolic_search.py tests/test_compilers.py
.venv/bin/python scripts/run_hwp_symbolic_study.py
```

## Frozen experiment

`configs/hwp-symbolic-study.yaml` records the 13 existing development inputs and
all 27 previous queries per input, plus five fresh cases: native sizes nine and
ten, two groups of five, and two seeded overlapping-predicate instances. The
fresh inputs have three fixed nonnegative preferences/constraints. Batch size
remains capped at eight; data and normalized terms remain capped at ten. The
configuration was written before inspecting variant resource results.

Five methods run in both construction spaces: eager frontier, eager guided search,
symbolic on demand, symbolic with primitive costs resolved up front, and symbolic
without partial-wave pruning. Cold measurements run the first declared query;
warm measurements run the full query sequence and charge frontier acquisition
once. Each method/repetition has a fresh rotation cache. Symbolic summaries,
rotations, and emitted templates persist within warm sequences; target solutions
and search labels do not. Three individual timing samples are retained.

The runner checks original-space outcomes against archived development optima,
cross-checks completed methods against each other, and tests every returned bound
against available optima. Timed selective runs do not emit every option. Input
loading and any normalization-scale acquisition are recorded and charged in report
totals. Python process startup and final result serialization are excluded; cold
means an empty synthesis cache, not a fresh interpreter. Strong batching references
are acquired separately, with completion flags.
An incomplete DP gets lower bound zero, never a fabricated optimum. Gap-threshold
timestamps record in-loop observations. When an optimal result closes only as the
queue empties, a null intermediate timestamp means the final `stats.seconds` is
the available closure observation; the final `L`, `U`, and status remain authoritative.

Evidence and measurements are in `results/hwp-symbolic-study.json.gz`; the concise
comparison is `reports/hwp-symbolic-study.md`. Any certified strict quality win
is replayed into `results/hwp-symbolic-witness.json.gz` with the existing program,
candidate, lowering, and verification schemas. Results separate H1 (equal-quality
end-to-end evaluation cost) from H2 (verified construction quality). Memory
profiling is a separate diagnostic run, excluded from timing samples; its phase
peaks cover traced Python allocations, not all native numerical-library memory.
The original study artifacts are retained unchanged. No downstream optimization,
publication, or expansion beyond this arithmetic variant is part of the experiment.

## Measured outcome and stopping decision

The completed study contains 1,080 timing samples, 90 separate memory samples,
and 11,520 query results: 10,622 `OPTIMAL`, 778 `FEASIBLE` with open gaps, and
120 `INFEASIBLE`. All original development intervals were checked against their
archived optima; completed methods were cross-checked, and all proposed
incumbents passed emitted verification. The evidence source, runner, and frozen
configuration hashes match the implemented files.

H1 is supported narrowly for cold queries on the 11 original-space inputs where
both the frontier and symbolic methods completed every matched query in all
three repetitions: the sum of per-case median totals is 5.0675 s versus 3.9041 s
(about 23% lower). All three paired aggregate repetitions favor symbolic search.
For the corresponding warm sequences, the frontier totals 6.2534 s and symbolic
search 6.5184 s; there is no repeatable warm advantage. The full workload has
unequal certification rates. Lower aggregate time on that mixed-status workload
is not an equal-quality speedup. Upfront rotation refinement often outperforms
on-demand refinement here, and disabling partial-wave pruning increases search
work. Weak unresolved bounds and wave exploration still limit larger inputs.
These results do not justify a general speedup claim.

H2 is supported for three fixed queries across native sizes six and seven. The
new optimum `(204,68,4)` improves the old `(204,74,4)` by six scheduled T layers,
with identical T-count and allocation. The native-six preference has objective
`93/130 -> 183/260`, a 1.61% improvement. The strongest expanded batching baseline
also finds the improved circuit, so the benefit belongs to the arithmetic
ordering and is not exclusive to the symbolic controller. A separate dense
verification of the saved native-six witness measures operator-norm error
`3.378761618948357e-5`, below the `1e-4` budget. Its ordinary depth equals wave
depth because it has one wave.

Stop this milestone at the tested arithmetic family. No accumulation,
measurement-assisted cleanup, catalysts, new solver, or precision-policy change
was added to rescue the timing results. Broader construction or scheduling work
would be a separate experiment.

## Subsequent interleaving milestone

The experiment above remains a historical frozen result. The current library
also offers compressor-level timing transfers (`evaluator='transfer'`, now the
default); `evaluator='graph'` retains the earlier evaluator for comparison.
`symbolic_search(..., interleave=True, coupled_bounds=True)` enables resumable
partial-wave families and certified global resource-load bounds. See
[`hwp-interleaved-plan.md`](hwp-interleaved-plan.md) for their proofs, boundaries,
validation gates and separate experiment. These changes do not expand the
staged/readiness arithmetic construction family.
