# Constrained nine-rotation diagnosis

The declared experiment keeps the existing staged/readiness recipes, normalized
term precision, unitary cleanup, original boundaries, and complete-wave model.
It addresses the native-nine query with three clean ancillas and wave depth at
most 200. The prior warm query stopped at T=468 despite a completed reference
at `(354,58,3)`. Configuration is in `configs/hwp-nine-study.yaml`.

## Search changes and certificates

`symbolic_search` has three independent opt-in switches:

- `pareto_ties=True` retains equal scalar-cost work, accepts lexicographic resource
  improvements, and prunes an equal-cost family only if its componentwise lower
  resource tuple cannot improve the incumbent's resource tuple. Existing exact
  Pareto labels at compatible closed boundaries remain in place; incomparable
  depth/workspace prefixes are never collapsed to a scalar local optimum.
- `partition_bounds=True` adds an integer block-size relaxation for T-count. For
  each group and each eligible size, take the least certified block T lower
  bound among subsets of the remaining terms. Solve an unbounded size-partition
  DP summing to that group's remaining cardinality, then sum over groups. Any
  actual partition maps to an admissible relaxed partition, so the result is a
  lower bound. Reusing the cheapest subset, ignoring data conflicts, and ignoring
  wave workspace packing only relax feasibility. Cache it by refinement epoch
  and remaining term set. No unproved synthesis-cost estimate is introduced.
- `progress_order=True` prefers more covered terms at equal scalar bounds, then
  the relaxed resource tuple, then insertion order. This is an exploration
  heuristic, not a stronger certificate. It retains every pending family.

The default remains scalar search. `OPTIMAL` still means the rational scalar
cost is proved minimal in the declared finite model. With endpoint search, check
`stats['endpoint_certified']` separately: it is true only after exhausting all
families that could improve the lexicographic optimal resource tuple. This
certifies one nondominated endpoint, not an entire Pareto frontier. A timeout,
target stop, or tolerance stop may have a scalar certificate without an endpoint
certificate. `incumbent_history` records verified improvements, including tied
scalar costs, and `scalar_certified_seconds` records scalar gap closure.

For nonnegative objective weights, a resource tuple that dominates an optimal
endpoint has either lower objective cost or equal cost and a lexicographically
smaller tuple. Thus completed lexicographic endpoint search returns a
nondominated point. Equal-cost pruning uses componentwise resource lower bounds,
not an arbitrary ordering of unfinished recipes. Full emitted verification is
required before accepting each incumbent.

`seeds` is a diagnostic interface. Plans must reference this library's option
IDs. Seed resources, coverage, boundaries, footprint compatibility, and emitted
semantics are checked before use. The study keeps seeded runs separate from all
timed method comparisons.

## Independent partition comparator

`hwp_partition.partition_frontier` handles disjoint singleton predicates. It
checks all subsets in each group for the same available `(boundary, resources)`
menu at a given block size. It rejects overlapping predicates and unequal menus.
Within this checked domain, exchanging equal-angle singleton terms only renames
data wires. Enumerating integer size partitions therefore covers every subset
partition up to that symmetry.

For each size partition it retains nondominated local recipes, then independently
enumerates legal wave packs of the selected blocks. A wave has one original
boundary, additive scratch, and maximum block depth; waves serialize and scratch
is reused. The scheduling DP anchors the first block in the earliest remaining
boundary. It never calls the production wave enumerator or symbolic lower bound.
Its complete frontier is exact within the same supplied native construction
family, including multiple disjoint angle groups. It is not a solver for the
general overlapping-predicate domain.

Timed partition runs use the same compact symbolic evaluator, resolve only
individually workspace-eligible recipes, and lower only incumbent circuits.
This avoids charging them for an unnecessary eager graph for every recipe.
Separate reference runs use the independently built eager library and compare
its complete frontier with generic-wave DP.

Strong uniform/per-group batching is retained separately. Its completion proves
only restricted-family completion. A no-depth-cap partition certificate cannot
be substituted for a constrained schedule certificate.

## Protocol and checks

Run:

```bash
.venv/bin/python scripts/run_hwp_nine_study.py
.venv/bin/python -m pytest
```

Six methods isolate the old scalar controller, tie handling alone, tie handling
plus queue ordering, tie handling plus partition bounds, all three changes, and
the independent partition baseline. Budgets are 1, 3, 10, and 30 seconds, with
three repetitions and rotated method order. Cold runs the constrained query
first. Warm runs a separate equal-budget count query before the constrained one.
Every independent trial owns fresh synthesis/library caches. The runner imports
backend dependencies before timing without synthesizing rotations. Input,
library construction, refinement, unsuccessful search and verification are
charged. Actual deadline overruns are recorded.

Separate references compare complete generic-wave and native-partition frontiers
and strong batching. A reference witness is replayed through remaining-set
bounds, then supplied only to separately labeled seeded diagnostic runs. Raw
records retain input/configuration, source hashes, query fingerprints, plans,
verification, bounds, histories, label/queue peaks, and warm-up outcomes.

The coupled follow-up uses the existing two-group/one-carry witness plus one
prospectively declared new angle pair. It sweeps six depth caps and one/two
ancillas, comparing the original controller, combined controller, partition
baseline, and strong batching against completed references. These are mechanism
probes; a single fresh pair does not establish generalization or novelty.

Tests compare complete endpoints and partition frontiers with independent tiny
partition/wave enumeration, check the count relaxation at every remaining set
and successive refinement, exercise zero-weight objectives and boundaries, reject
invalid seeds/domain assumptions, and interrupt refinement, bounds, expansion,
and emission while checking certificate safety.

The generated [study tables](../reports/hwp-nine-study.md) report fixed-budget
attainment and endpoint completion separately. The [analysis](../reports/hwp-nine-analysis.md)
records the interpretation and remaining limitations.

After the study, run `python scripts/check_hwp_nine_results.py` to check the saved
source hashes, reload and independently emit every distinct saved incumbent,
compare one locally optimal plan per group with its exact global rescheduling,
and densely verify the two one-ancilla/depth-100 coupled witnesses. This writes
`results/hwp-nine-validation.json.gz`; it is separate from the timing data.
