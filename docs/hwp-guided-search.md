# Cost-directed HWP experiment

Implementation base: clean `research/hwp-pareto-synthesis` commit
`47d71a791413a85776cdf9f517a6a237b3e510d5`, found in the existing local worktree.
The saved study was executed at `febb7bd6669bdcce506f6878549877ca6b6b8059`;
all recorded source hashes still match. The later commits add the implementation,
runner, tests, and results. No source was reconstructed from the evidence-only branch.

The source audit confirms all nonempty compatible subsets up to the batch cap,
normalized-term precision allocation, singleton direct options, native in-place
and copied-parity HWP, original block boundaries, and complete waves with disjoint
data footprints. Wave T-count adds, wave depth takes the block maximum, and scratch
adds within waves and is reused after clean complete-block boundaries. Full-plan
T and wave depth add; peak scratch takes the maximum. Emission verifies composition
and counts ordinary scheduled depth separately; model certificates concern wave depth.
The existing exact DP and baseline enumeration are retained unchanged.

The original timeout returns feasible complete plans but no gap certificate.
The new search must retain the active expansion's bound on interruption.
Dominance applies only at the same remaining terms with scratch restored.
All cost arithmetic uses exact fractions. A cost-optimal representative need not
be lexicographically optimal in resources when some weights are zero.

The frozen configuration adds native sizes two and seven, three equal-angle groups,
and six overlapping parities sampled with seed 20260920. It fixes all preferences,
resource limits, the eight-ancilla envelope, and shared normalization scales before
search. No downstream optimization or new construction is included in this milestone.

Run the baseline diagnosis with:

```sh
python scripts/run_hwp_guided_search.py --stage diagnosis
python scripts/run_hwp_guided_search.py --stage evaluate
```

See `reports/hwp-guided-diagnosis.md` and `results/hwp-guided-diagnosis.json`.
The complete supplied plan is preserved in `docs/hwp-guided-search-test-plan.md`.

The search shares the original canonical wave generator, extracted without changing
its transitions or within-cover Pareto pruning. The only other change to the
original library records its synthesis seed for the guarantee fingerprint. The
base source fingerprint check reads the pinned commit; current model fingerprints
include current source files, input, emitted templates and synthesis versions,
precision, batch cap, wave rules, scratch semantics, and the exact hard limits.

Structural bounds use exact fractions. Archived inequalities retain their source
search result, validate matching constraints and coefficients, and use the best
nonnegative single-certificate scaling. No approximate LP is used. Certificates
are trusted local search outputs, not a parser for arbitrary external claims.
Models are frozen contexts; do not mutate their libraries after construction.
A verification failure raises an error and produces no optimum/infeasibility claim.
`FEASIBLE` with reason `TIMEOUT` retains an incumbent and certified lower bound;
`TIMEOUT` without an incumbent is distinct from `INFEASIBLE`. Zero lower bounds
have no percentage gap, while zero-cost equality still proves optimality.

## Interpretation and stopping decision

The structural bound substantially reduces expanded prefixes and generated waves
relative to the same search with trivial bounds. Good reference seeds alone change
little search work here. Single-certificate transfer produces no additional state
or wave reduction on any held-out target, while acquisition adds work. This is a
negative result for the tested transfer mechanism, not evidence that arbitrary
combinations of certificates would fail.

The existing full-frontier DP is the preferred method for this small-instance,
many-query workload: charge its frontier once and it wins the overall sequence.
Structural pruning helps the new search relative to its controls, but does not
establish the main hypothesis of a faster replacement for the frontier at matched
total cost on this frozen set. In particular, native_8 often closes its query after
one expensive wave expansion; expanding fewer states does not avoid enumerating
and Pareto-pruning all waves for that state. The bottleneck is wave enumeration
in those queries. Full option-library construction is also material for cold small
queries, but the evidence does not justify adding the gated pricing experiment.

Stop at the three planned commits. Keep the exact DP for many-query use, retain
the tested search/bounds as an inspectable experiment, and defer stronger bounds,
on-demand options and new construction families. H2 is unestablished for the frozen
unrestricted costs. There is no claim of an all-weights impossibility result.

## Validation and unsuccessful attempts

The new six test groups and relevant existing semantic/resource tests passed
(79 tests total). They compare the search with the exact DP; independently enumerate
tiny completions and all remaining-term states for lower bounds; test constraint
fingerprints, corrupted certificates and floating-point bound rejection; interrupt
both between nodes and within successor generation; reconstruct returned circuits;
and retain the unsupported constrained witness. The focused six groups passed again
after hardening integer seed and rational certificate validation.

All 351 frozen cost/limit queries are compared across five methods with three
repetitions. Archive acquisition is separate and uses only the six development
weights at each exact constraint fingerprint. No target optimum is preloaded.
The runner checks all returned intervals against the reference optimum and verifies
every incumbent when it becomes an upper bound. The witness uses existing program,
candidate and lowered-circuit schemas, including full emitted gate events.

The first diagnosis attempt could not download the QED-C development input because
of a TLS connection failure. The existing local copy was reused and checked against
the manifest checksum. A complete preliminary timing run was superseded after
hardening the API against floating-point certificates; its results remain in ignored
`results/raw/hwp-guided-search/pre-validation-hardening/`. The final experiment was
rerun with the hardened code. These setup/validation attempts are not counted as
algorithm timings. No downstream optimization or construction expansion was attempted.

Raw repetition times, acquisition costs and certificates are in
`results/hwp-guided-search.json`; the compact comparison is in
`reports/hwp-guided-search.md`; the emitted finalist and exact interval are in
`results/hwp-guided-witness.json`. These guarantees concern the finite declared
wave model and precision policy, not physical runtime or post-optimization optima.

## Measured accounting details

| Method | Cold single-query totals, summed over all 351 queries (s) | Warm 27-query sequences, summed over inputs (s) |
|---|---:|---:|
| frontier | 305.9682 | 3.3491 |
| direct_trivial | 289.5432 | 14.0193 |
| reference_trivial | 339.1815 | 15.7901 |
| structural | 335.2428 | 11.8513 |
| archive | 352.5558 | 17.5891 |

Cold single-query totals are sums of measured components, modeling a fresh invocation for each query; they are not separately executed process timings. Each includes the measured import/setup startup, empty-cache library, model fingerprint setup, necessary seed/frontier acquisition, and query/verification time. Only held-out archive queries pay their constraint-specific archive acquisition. Warm totals charge common setup and acquisition once per input across all preferences and limits.

The report table counts query search states/waves (and one frontier computation). Archive acquisition additionally expands 586 states and generates 499717 waves; all its time is included in the acquisition column.

The persisted witness was also replayed independently through the existing dense verifier: status `verified_lowered_dense`, operator-norm error 2.5395573e-05, below the 1e-4 budget. Its modeled and ordinary emitted resources are both (284,166,3), and its normalized T-cost interval is [71/78,71/78].
