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
python scripts/run_hwp_guided_search.py
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
