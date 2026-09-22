# Interleaved HWP search and global coordination

This milestone combines resumable wave generation, selective rotation refinement,
compact timing evaluation, retained local alternatives, and a certified global
relaxation. It keeps the existing staged/readiness construction family, fixed
normalized-term precision policy, clean unitary block boundaries, and complete
waves. It does not introduce a new arithmetic family, within-block scratch reuse,
measurement, catalyst, or a claim against published HWP resource frontiers.

## Implementation and correctness contract

A closed prefix keeps all nondominated exact resource labels at the same remaining
term set. Local blocks are not reduced to one scalar optimum: all eligible
partitions/layouts/orderings remain available. This is sufficient only because
all completed blocks restore the same data interface and clean scratch. Retained
values, output-port timing, and scratch lifetimes would require a richer state
before local dominance could extend to a different scheduling model.

An open wave is a resumable family: chosen option IDs, covered terms, occupied
data footprint, next sibling cursor, and whether closing this wave is still
pending. Each queue visit closes a wave, scans one alternative, or refines one
shared rotation. Refinement also occurs before returning to a weaker sibling
cursor, so low-bound sibling enumeration cannot starve all informative children.
Refinement selects unresolved requests from a live viable partial wave by shared
use count. This is a heuristic, not a lower bound or a claim to optimal information
acquisition. Measured synthesis-cost pricing and critical-path sensitivity ranking
are later ablations, not silently assumed gains.

All queued and actively processed families contribute to the global lower bound.
A parent remains pending during refinement, bounds, child insertion, and emitted
verification. Old queue bounds remain conservative after shared refinement;
entries are recomputed and requeued on demand. Open families are not subjected
to closed-prefix dominance. Duplicate partial covers can have different allowed
continuations and must not be collapsed merely by resource triple.

The target query uses the existing hard ancilla/depth caps and an optional
`target_cost` for the fixed rational objective. It can stop after verifying an
incumbent at or below that target. Failure to reach a target before timeout is
not infeasibility. A proved full-family optimum above the target establishes
unattainability within this restricted model.

## Compact evaluation

The shared arithmetic scheduler returns compressor ports and weight outputs.
Emission turns these into operations; symbolic evaluation composes precompiled
forward/inverse compressor timing transfers, parity transfers, and phase ports.
No local PhaseProgram, Candidate, or Operation list is constructed during ordinary
transfer evaluation. This is still a representation of a specified recipe, not
inverse arithmetic synthesis or a claim of graph-free reasoning in every sense.

Each finalist is cross-checked against the retained high-level graph evaluator,
the emitted Clifford+T schedule, and semantic verification. Unequal-arrival tests
check the whole transfer at every output port. This preserves dependency timing
that a scalar count of Toffoli layers would lose.

## Certified global relaxation

For every remaining term i, consider all covering options j and divide a block's
resource load by its covered-term count |S_j|. Summing the minimum share for each
term cannot charge a selected block more than its total load. The existing T
bound uses this property. Within each original block boundary, additionally use:

- individual minimum block depth;
- for each data wire q, fractional loads d_j/|S_j| if j touches q, zero otherwise;
- scratch-time load a_j*d_j/|S_j|, divided by the available workspace A.

Blocks touching q cannot share a wave, so their depth loads add. In any wave,
sum(a_j*d_j) <= max(d_j)*sum(a_j) <= D_wave*A. Thus the workspace-volume bound is
also safe. When A=0, only zero-workspace options are eligible and that bound is
zero. Take the maximum of these bounds within a boundary and sum across original
boundaries, which cannot share waves. Unknown rotations still contribute zero.

For an open wave, combine chosen-wave depth and remaining depth using maximum,
then add completed-prefix depth. Remaining blocks may join the open wave.
Scratch adds among chosen parallel blocks and takes a maximum with the relaxed
remaining requirement. This deliberately relaxes some packing conflicts.

These explicit inequalities provide a first global coordination relaxation.
A full Lagrangian price optimizer is deferred: it would add another tuning factor,
and weighted local choices alone can miss unsupported discrete Pareto points.

## Test and comparison gates

1. Check every small remaining state and successive refinement against independent
   partition/wave enumeration; test native, overlapping and boundary-separated inputs.
2. Compare both interleaved modes and upfront refinement with exact small optima,
   including pure depth/workspace objectives, infeasible caps and zero costs.
3. Interrupt scans, refinement, closing, bounds and materialization; ensure no
   unexplored family disappears from the certificate.
4. Use a clearly abstract two-block witness: (T,D,A)=(20,10,4) versus (20,12,2).
   With A=4, locally fastest choices need depth 20; globally coordinated smaller
   choices need depth 12. This is a scheduler regression, not physical HWP evidence.
5. Run the frozen development configuration with equal per-query budgets, charging
   setup and final verification. Compare serial graph/transfer evaluation,
   upfront costs, interleaving, coupled-bound ablations, and strong batching.
6. Separately compare complete exact frontiers, strong batching, and the heuristic
   that keeps one locally optimal plan per angle group then reschedules globally.
   Incomplete references never establish a quality win or full infeasibility.

Report verified incumbents and gaps at fixed budgets, completion counts, first
incumbent/improvement, graph/recipe/evaluation/refinement counts, wave expansions,
actual elapsed time and overruns. Compare speed only on matched complete outcomes;
include failures and no-incumbent cases in fixed-budget summaries. Fresh holdouts,
longer-budget scaling, new arithmetic actions and release/reuse remain subsequent
experiments, contingent on this result.

## Measured result

See [the outcome analysis](../reports/hwp-interleaved-analysis.md). Interleaving
improves fixed-budget completion on the development study; the coupled relaxation
does not improve completion and remains optional. The physical two-group witness
confirms that independently optimal local choices can fail a global depth cap.
The current recommendation is `interleave=True, coupled_bounds=False` for this
workload. Raw library timing counters can be nested (`summary_seconds` includes
graph/recipe construction on a cache miss); do not sum them as exclusive phases.
End-to-end measured query time is the authoritative timing metric.
