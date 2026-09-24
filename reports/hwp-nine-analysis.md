# Constrained nine-rotation outcome

Scope update: this count-first endpoint diagnosis is historical evidence. The
active mixed-cost protocol is [here](../docs/hwp-linear-cost-evaluation.md).
Further endpoint certification is a superseded priority, not an error in these
recorded results.

The block-size partition bound repairs the observed scalar-search failure;
Pareto-aware tie handling alone does not. Progress ordering improves which
minimum-T endpoint is reached. The independent native partition/scheduling
method is the stronger solver on this checked domain: it both obtains and
certifies the endpoint efficiently. The generic controller's scalar certificate
must not be confused with completed endpoint optimization.

The reproducible protocol is in [the experiment description](../docs/hwp-nine-experiment.md),
the full tables in [the study report](hwp-nine-study.md), and raw evidence in
`results/hwp-nine-study.json.gz`. All timing comparisons use the same recipes,
precision policy and complete-wave resource semantics. The native partition
baseline uses the same compact evaluator and avoids lowering nonfinalists.
Separate reference runs use the eager library and generic-wave frontier.

## What the experiment distinguishes

The original constrained native-nine query uses three available ancillas and a
wave-depth cap of 200. Its direct incumbent is `(468,52,0)`; the completed
minimum-T endpoint is `(354,58,3)`. The cap of 200 also permits the same T-count
using three serial blocks at `(354,174,1)`. Thus fixing this query's scalar gap
alone does not establish a gain on a binding depth/workspace conflict.

The completed eager reference agrees with the native partition method on all
seven constrained frontier points. All 25 generic-wave references and all 25
strong-batching references completed. The witness replay has a fractional root
T lower bound `1764/5 = 352.8`; the integer partition relaxation gives 354. Even
when explicitly seeded with the verified optimum, the original controller and
tie-only variant stop after three seconds at `L=1060/3, U=354`; the combined
variant closes the scalar gap. This separates weak-bound certification work
from incumbent discovery, without supplying those seeds to the timed trials.

The warm reproduction spends its budget scanning partially generated waves with
no new rotation refinement. Weak fractional cost bounds keep many unfinished
families ahead of complete T=354 candidates. The size-partition relaxation keeps
integral block cardinalities and raises the relevant lower bounds. Seeded
witness diagnostics are reported separately; they test certification with a
known feasible solution and are never used to improve timed search outcomes.

Equal-cost pruning was previously intentional scalar-search behavior: once
T-count was certified, the controller stopped. The new endpoint mode continues
that work and permits equal-cost resource improvements. Its lexicographic
selection is explicit; incomparable depth/workspace choices remain available at
compatible boundaries. `endpoint_certified` records when all improving families
have actually been ruled out. Merely returning the known optimal tuple does not
set that flag.

In all three three-second cold trials, the original controller returns
`(468,52,0)`, tie handling plus the partition bound returns `(354,174,1)`, and the
combined controller returns `(354,58,3)`. The two modified controllers certify
T=354 but do not complete endpoint search at that budget. The native partition
baseline returns and certifies `(354,58,3)` in a median 0.4759 seconds. This is a
fixed-budget controller gain and a negative result for competitiveness with the
specialized method on this native input.

All 144 native timing trials completed. At the thirty-second budget, medians
separate scalar closure from complete endpoint search:

| Method | Cold scalar certificate s | Warm scalar certificate s | Endpoint certified (cold/warm) |
|---|---:|---:|---|
| Original scalar controller | 5.8261 | 5.3300 | Not requested |
| Ties plus partition bound | 1.7495 | 0.1297 | 0/3, 0/3 |
| Combined changes | 1.0035 | 0.0551 | 0/3, 0/3 |
| Native partition baseline | 0.5012 | 0.0931 | 3/3, 3/3 |

The modified endpoint searches consume the thirty-second budget even after their
scalar certificate closes. All four methods return `(354,58,3)` at this budget;
the difference is when it is reached and what the search itself proves. The
original method deliberately stops at scalar certification, so its missing
endpoint flag is not an attempted endpoint proof that failed. At one second,
all three combined cold trials still return T=468; their warm counterparts reach
`(354,58,3)`. Warm-up work has its own charged budget.

The thirty-second cold trials expose the remaining enumeration cost. Median
sibling scans are 973,789 for the combined controller, despite only two retained
closed-state labels at peak. The independent partition method solves 23 size
partitions using 54 cached scheduling subproblems. These counters have different
units; they describe the mechanisms rather than constitute a speedup ratio.
The generic open-wave family retains labeled subset/cursor distinctions, while
the specialized method quotients only the exchangeable native domain.

## Scope

The partition baseline independently enumerates group size partitions and exact
wave packing after checking disjoint singleton predicates and exchangeable
resource menus. Its seven-point constrained frontier includes the alternatives
`(354,58,3)`, `(354,116,2)`, and `(354,174,1)`. It rejects overlapping predicates;
its efficiency cannot simply be transferred to that larger domain.

The two-group follow-up tests actual coordination: a cap can be individually
satisfied by each group's locally preferred circuit while their combined
workspace schedule violates it. The existing angle pair is a development
witness; the second angle pair is a prospective mechanism probe, not a broad
holdout suite. Strong batching is kept as a separate restricted reference.

All results concern this finite unitary construction family, fixed precision,
and complete-wave model. They do not establish superiority over published HWP
constructions, a new arithmetic construction, within-block scratch reuse, or
global optimality over arbitrary circuits. Emitted-circuit depth is recorded
separately and is not substituted for the certified complete-wave depth.

## Coupled probes and validation

There are 24 coupled queries (two angle pairs, two ancilla caps, six depth caps),
with four timed methods: 96 additional trials. Original, combined, and partition
methods all certify 20 feasible scalar optima and four infeasible cases. Both
endpoint-capable methods certify all 20 feasible endpoints. Strong batching
matches every feasible minimum T-count; the completed references resolve its
restricted-family feasibility. The timed batching wrapper retains FEASIBLE or
TIMEOUT statuses rather than issuing full-family certificates; its four
no-incumbent depth-50 rows are not evidence of an enumeration timeout.

At one ancilla and depth 100, the old pair's local choices are `(114,56,1)` and
`(110,54,1)`, requiring depth 110. The new pair's choices are `(108,54,1)` and
`(114,56,1)`, again requiring 110. Exact rescheduling of those fixed choices is
infeasible in both cases. Coordinating alternatives recovers `(258,56,1)` and
`(264,54,1)` respectively. Dense emitted verification gives operator-norm errors
`3.843243638793904e-5` and `3.623137776792518e-5`, below the common `1e-4` budget.

With two ancillas and caps 110/120, scalar-only search sometimes selects a
serial minimum-T endpoint while endpoint mode selects the parallel alternative.
These trade depth against workspace; the parallel alternative does not dominate
the serial one. At the binding caps, all methods find the same optimum. Median
coupled-query times are approximately 0.276 seconds for combined and 0.277 for
partition. Each coupled query has one timing observation, so that small difference
is not convincing efficiency evidence.

Final validation: **234 tests passed**. The independent replay checked all
19 distinct saved incumbents and 24 local/global queries; both physical witnesses
passed dense verification. Saved source/config hashes match the implementation.
Maximum measured deadline overrun across all 312 timed query outcomes is
0.0288 seconds. Raw replay evidence is in `results/hwp-nine-validation.json.gz`.

## Recommended use

Use the native partition method when its checked disjoint/exchangeable domain
applies. Keep the generic controller and its existing default for broader input
families; the new partition bound and progress ordering are opt-in tools for
improving incumbent and scalar-certificate latency. Request `pareto_ties=True`
when an endpoint proof matters, and inspect its completion flag. These results
do not justify spending a full endpoint budget for a count-only request.

A further controller-quality experiment should use fresh overlapping predicates
with binding depth/workspace limits, where native size symmetry is unavailable,
and include completed strong references. The present coupled disjoint probes
confirm the mechanism but do not expose a construction advantage over batching.
