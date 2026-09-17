# Finite-library HWP Pareto synthesis

## Scope and provenance

Implementation follows [the frozen plan](hwp-pareto-plan.md), starting at
`7683dcacba6731e39b242085fb5ec8ec236b1c45`. The subsequent ARA governance commit
was carried into the isolated worktree. Historical `search.py` and the
single-demonstration runner are unchanged.

Given a diagonal `PhaseProgram`, `build_library` normalizes its predicates and
emits every compatible nonempty subset through a declared maximum batch size.
Each option has a covered-term mask, original block boundary, data footprint,
compact wire mapping, constructor/layout, emitted circuit, verified synthesis
bound, and measured `(T, T-depth, clean scratch)`.

The current cap is eight normalized terms in the study; the API defaults to a
maximum of ten terms and rejects more than ten data qubits because the existing
ideal verifier requires exhaustive data-basis checks. No large-instance or
unrestricted optimality claim follows from this implementation.

## Executable construction audit

| Entry | Source / adaptation | Applicability | Cleanup and accounting |
|---|---|---|---|
| Direct phase | Existing `compile_independent` | One normalized affine-parity contribution | Compute/phase/uncompute; no additional workspace |
| In-place HWP | Kivlichan et al., arXiv:1902.10673v4 Appendix A.1; existing constructor | Distinct positive singleton predicates after normalization | Reversed staged arithmetic restores data and carry scratch |
| Copied-parity HWP | Same staged arithmetic plus explicit parity materialization | One compatible normalized angle/coefficient group | Reverse arithmetic and parity preparation; parity wires and carries both counted |
| Batch variants | Enumerate every subset up to the declared cap | Original block/angle/coefficient compatibility required | No hidden retained state across complete blocks |

Forward and reverse Toffolis use the existing exact seven-T, three-T-layer
Amy–Maslov–Mosca–Roetteler primitive (arXiv:1206.0758v4), followed by scheduling
of the emitted stream. Scalar Toffoli estimates never replace emitted costs.

Kivlichan Appendix A.2 also describes accumulation of partial population counts
in a total-weight register using roughly square-root workspace. This changes
the arithmetic: add partial weights, clean temporary computation, phase the
total, then recompute/subtract partial weights to clean the accumulator.
It is a genuinely different library option, not equivalent to independently
phasing batches. Its unitary adaptation requires explicit additions and
recomputation; it is **not implemented in this first finite library**. Published
measurement-cleanup costs cannot be substituted for emitted unitary costs.

Measurement-assisted HWP and Kan–Symons catalyzed HWP
(arXiv:2411.02160v2) are also omitted. No comparison with the full published HWP
frontier, or with physical surface-code runtime, is claimed.

## Precision contract

For N normalized terms and total error epsilon, each term owns epsilon/N.
An option covering k terms receives k*epsilon/N, divided equally over its actual
generic rotations. Exact rotations introduce zero approximation error. Cache
keys include the precise angle, tolerance, backend version, and seed.

A composed candidate stores `term_error_blocks`: contiguous operation ranges
and the normalized term IDs each range covers. Lowering and the independent
verifier check exact term/operation coverage and derive the block tolerances.
All selected block rotations are preserved during composition; there is no
second synthesis or silent global reallocation. The sum of selected blocks'
measured errors remains bounded by epsilon. Constants and affine complements
retain the common normalization's global phase. No resource states/reuse counts
are accepted with this precision policy.

## Wave model and exact recurrence

A wave consists of complete blocks on disjoint data footprints with distinct
scratch allocations. It reserves those wires for the whole wave and returns
scratch clean. Blocks cannot cross original `PhaseBlock` boundaries; waves
respect those boundaries. Within a diagonal block, complete waves commute.

For a wave W:

```
T(W) = sum(T_j)
D(W) = max(D_j)
A(W) = sum(A_j)
```

For sequential waves, add T and D and take the maximum A. This is a conservative
logical T-depth schedule, not physical elapsed time. The artifact records each
wave and its barrier; the ordinary emitted gate stream has no barrier gate.
The independent scheduler may find a smaller depth when barriers are removed.

`frontier` memoizes the Pareto labels for each remaining-term subset. The next
wave contains the first remaining term: commuting complete waves can always be
reordered into this canonical form within an original boundary. Every compatible
wave containing that term is considered. Dominance pruning is restricted to the
same remaining subset, or to wave alternatives with identical term coverage.
All boundary interfaces restore data and clean workspace, making resource
composition monotone and this pruning sound for the model.

One deterministic reconstruction is retained for each tied resource tuple.
The resulting model frontier is exact only within the enumerated library,
precision policy, and wave model. Emitted and post-optimization frontiers are
candidate sets: discarded model-dominated or tied circuits may optimize better.

## Acceleration and limits

- Compact-wire templates share synthesis and verification for genuinely
  identical predicate structures; native equal-angle subsets share by size.
- The existing persistent rotation cache includes angle/tolerance/seed/version.
- Canonical waves eliminate equivalent permutations of complete waves.
- Memoization shares continuation searches; Pareto pruning removes dominated
  resource labels, and caps exclude impossible waves/plans.
- A serial direct circuit supplies a cheap feasible incumbent when applicable.

The solver still uses term subsets, including for native inputs. It does not
claim a count-state symmetry reduction, branch-and-bound lower-bound engine,
CP-SAT backend, or scalable heuristic. These can be motivated by measured
bottlenecks rather than added preemptively.

Timeouts return complete feasible circuits with `FEASIBLE`, or `TIMEOUT` if no
incumbent was recovered. Only completed searches can report `OPTIMAL` or
`INFEASIBLE`. Queries outside the solved resource range are rejected.

## Baselines and validation

Baselines enumerate every global cap and every per-group cap/layout, using both
balanced batching and full-size batches plus a remainder, with direct synthesis
allowed for each batch independently. This avoids forcing unprofitable HWP on
small remainders. Membership assignments
are exhaustively enumerated, not fixed to contiguous predicates. Their complete
blocks receive the same exact wave scheduler. The base-HWP reference reconstructs
the existing constructor's operations and uses the same block error budgets.
Direct synthesis retains its naturally parallel schedule.

All retained parents receive the same one-pass PyZX `zx_extract` opportunity and
independent parent-to-child verification. Both parents and verified children
remain eligible. Failed/timed-out optimizations are recorded. Synthesis, search,
baseline scheduling, emission/verification, and postprocessing times are separate.

Tests use an independent partition-then-wave enumerator through six terms,
check full-circuit emission/replay, boundaries, empty normalized programs,
scratch reuse, nonuniform precision, mutation rejection, infeasible/timeout
status, and preservation of unsupported Pareto points. Existing construction
and verification regressions remain required.
