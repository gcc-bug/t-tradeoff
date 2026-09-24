# Interleaved HWP: outcome and next decision

Scope update: these controller and construction results remain historical
development evidence. The active objective is the [fixed mixed linear cost](../docs/hwp-linear-cost-evaluation.md).

Interleaving improves the controller on this development workload. Retaining
alternatives also resolves a real HWP case where independent local optima cannot
meet the global depth limit. The new global load relaxation is sound but adds
runtime without improving completion counts in the timed study.

The reproducible [comparison](hwp-interleaved-study.md) contains 504 trials and
756 query outcomes: six inputs, seven methods, two budgets, cold/warm modes,
and three repetitions. Each method has 108 query outcomes. Input loading and
library setup are charged to the first query; all rotation refinement, failed
search work and emitted verification are charged. Imports/process startup and
final serialization are excluded. The measured maximum deadline overrun is
0.0405 seconds. Warm queries have separate equal budgets and share only their
trial's caches. The recorded source/config/runner hashes match the implementation.

## What improved

| Controller | Certified optima / 108 queries | Remaining feasible, open gap |
|---|---:|---:|
| Serial graph evaluation | 81 | 27 |
| Serial compact transfers | 81 | 27 |
| Upfront rotation refinement | 84 | 24 |
| Interleaved refinement | 96 | 12 |
| Interleaved plus global load bounds | 96 | 12 |
| Upfront plus global load bounds | 84 | 24 |

All six controllers returned verified incumbents on these queries. Comparing
interleaved versus upfront **with the same global load bounds**, 12 paired
case/query/budget/cache/repetition samples have strictly better incumbents and
96 tie; none are worse. The 12 wins are repeated measurements of native-seven
count queries at one second and native-nine count queries at three seconds,
in cold and warm trials. They are not 12 independently discovered circuit gains.
Unequal certification counts are not an equal-quality speedup claim.

A matched example is native seven, count objective, four ancillas, three-second
cold trials. The median total time is 0.6424 seconds for ordinary interleaving
versus 1.1193 seconds for upfront refinement, and both certify T=204. Both refine
16 rotation keys. Interleaving generates 169 partial waves versus 19,297 for the
upfront serial wave expansion. This supports earlier feedback and incumbent
acquisition as the mechanism, rather than avoidance of rotation synthesis.
With the global bounds enabled on both sides, the corresponding medians are
0.7472 and 1.1311 seconds, still at the same optimum.

On native nine at three seconds, ordinary interleaving certifies T=310 in all
three cold repetitions (1.0713–1.1532 seconds). Upfront refinement times out with
T=468. The coupled-bound version also certifies 310, but takes 1.9773–2.0633
seconds. A separate independent subset-partition oracle in the tests confirms
310: without a depth cap, any partition of individually workspace-feasible blocks
can be run serially, so the minimum-T partition problem is exact. The longer
full-wave DP and strong batching references do not complete this count query;
their incomplete outputs do not establish a construction-family quality win.

## The local/global issue in a physical circuit

The separate development witness uses two disjoint equal-angle groups of three
inputs, angles 0.173 and 0.291, one clean ancilla, depth at most 100, and total
operator-norm error budget 1e-4. It uses the same precision policy and both
arithmetic orderings as the controller study.

Each group independently minimizes T-count with one available ancilla:

| Choice | T-count | Complete-wave T-depth | Workspace |
|---|---:|---:|---:|
| First group's local optimum | 114 | 56 | 1 |
| Second group's local optimum | 110 | 54 | 1 |
| Both local choices, necessarily sequential | 224 | 110 | 1 |
| Globally chosen feasible circuit | 258 | 56 | 1 |

The local choices cannot meet the depth cap even after exact global rescheduling.
The global solution retains HWP for the first group and uses three direct
rotations for the second group, all in one wave. It spends more T gates locally
to make the complete circuit feasible. The interleaved solver and independent
full frontier both certify this constrained optimum. Strong per-group batching
also finds it: the evidence supports retaining and coordinating alternatives,
not an exclusive new controller construction.

The saved emitted circuit passes dense clean-input isometry verification with
operator-norm error 3.843243638793904e-5, below 1e-4. Configuration, local plans,
complete reference flags, reconstruction, emitted circuit and verification are
in `results/hwp-local-coordination.json.gz`. Reproduce with:

```bash
.venv/bin/python scripts/check_hwp_local_coordination.py
```

The main timing study's separate local-choice diagnostic optimizes each group
under its ancilla cap but without a local depth cap; it is not the strong batching
baseline. In particular, its single-group depth failure is not evidence of
inter-group coupling. In the physical witness above, both independent local
depths already satisfy 100 individually, so imposing that necessary local depth
cap still leaves the global resource conflict.

This witness was declared as a mechanism test after implementing the controller;
it is not a holdout, and it is separate from the frozen timing workload. The
abstract depth-20 versus depth-12 scheduler test is also retained, but is not
presented as physical HWP evidence.

## What did not improve

The coupled relaxation gives the same 96 certified outcomes as interleaving
without it, and is slower on important cases. In the main count-only query,
with no depth cap, its stronger depth bound cannot improve the objective bound.
Even on the declared constrained queries it adds no completed outcomes here.
It remains an optional experimental bound, not a demonstrated performance gain.
No Lagrangian optimizer or estimated generic-rotation lower bound was added.

Compact transfers reduce high-level graph construction to finalists. On the
native-seven three-second cold example, serial graph evaluation builds 17 graphs
and serial transfer evaluation builds two. Both generate 31,605 partial waves
and certify the same optimum; their median times are about two seconds. Removing
graph construction alone does not resolve the search bottleneck.

Native-nine constrained-count warm queries still have open gaps at three seconds,
including with interleaving. The verified incumbent has T=468, while the separate
completed full-family reference finds T=354. Better completion is not universal
scaling. The strong timed batching implementation also spends substantial budget
on eager setup/enumeration; its restricted-family completion is never labeled
full-family optimality. Longer completed references, rather than these timing
failures, determine family-quality comparisons.

The existing overlapping-six `(284,166,3)` constrained witness remains better
than the completed strong batching point `(312,156,0)` under that query. This is
a previously established witness from the existing family, not a newly discovered
benefit of interleaving. Other completed native/group reference comparisons match
strong batching. No superiority over published HWP methods follows.

## Recommended next use

Use `interleave=True` with compact transfers for further development. Keep
`coupled_bounds=False` as the inexpensive default until a declared workload
justifies the additional bound work. Retain all eligible subcircuit choices and
exact compatible-boundary Pareto labels; do not replace them with independent
local scalar optima. `target_cost` is available for verified target attainment,
with ordinary bounds/status retained on timeout.

The next experiment should explain the remaining native-nine constrained-query
failure and test fresh inputs and longer budgets. More elaborate information
pricing, direct arithmetic-action generation, precision reallocation, and
within-block release/reuse are separate hypotheses. The current milestone still
evaluates and composes specified arithmetic recipes, with clean block boundaries.

Validation: the complete repository suite passed 218 tests, followed by the new
independent native-nine partition-certificate test. Tiny exhaustive comparisons
cover both refinement orders, pure count/depth/workspace objectives, original
boundaries, overlapping predicates, target queries, and interruptions. Every
recorded incumbent passed emitted verification; completed optima and available
reference bounds were cross-checked. The serialized physical witness was also
reloaded and independently reverified. No publication or push was performed.
