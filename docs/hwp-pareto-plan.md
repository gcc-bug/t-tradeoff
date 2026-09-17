# Implementation plan: resource-constrained HWP synthesis

## Branch and repository decision

Use a **new branch in the existing `gcc-bug/t-tradeoff` repository**:

- Branch: `research/hwp-pareto-synthesis`
- Base: `7683dcacba6731e39b242085fb5ec8ec236b1c45`
- Base branch: `research/ancilla-iterative`, reconfirmed at this commit when preparing this plan.

The input representation, audited HWP constructors, lowering, resource scheduler, and corrected verification are reusable. A new repository would duplicate these components and split their correctness fixes. A new branch separates the new scientific question from adaptive pass-order experiments.

At implementation time read repository instructions, inspect local changes, and preserve any uncommitted work. A separate worktree is preferred. After fetching the relevant remote branch, create the worktree from the pinned commit, for example:

```bash
git fetch origin research/ancilla-iterative
git worktree add -b research/hwp-pareto-synthesis ../t-tradeoff-hwp-pareto 7683dcacba6731e39b242085fb5ec8ec236b1c45
```

If the proposed branch already exists, inspect and reuse it rather than reset it. The branch and worktree have not been created by this planning task.

## 1. Goal and hypothesis

Given a phase operation, a library of valid constructions, an approximation budget, and resource limits, generate an actual circuit minimizing the requested resource cost.

Initial query:

    minimize T-count
    subject to T-depth <= D_max
               additional clean workspace <= A_max
               operator-norm error <= epsilon

The first research hypothesis is:

> Jointly choosing batch partitions, implementations, and parallel execution can expose useful complete-circuit tradeoffs missed by the best uniform batching strategies.

Do not assume this hypothesis is true. Solving the restricted problem exactly is initially a diagnostic: it determines whether this construction space contains a gain worth pursuing. Adding an integer solver or drawing a frontier is not itself the research contribution.

Dynamic preferences are no longer a requirement. Existing resynthesis tools remain common evaluators or library-building tools. Do not expand adaptive pass search during this milestone.

## 2. What to reuse and what to leave alone

Reuse `ir.py`, preprocessing, `baselines/independent.py`, `baselines/hwp.py`, arithmetic, lowering/synthesis, `resources.py`, and verification. Preserve the scratch-boundary and emitted-stream mutation regressions.

The base already implements in-place HWP for applicable singleton predicates, copied-parity HWP for general inputs, and an independently checked exact seven-T, three-layer Toffoli. Do not reimplement those repairs.

Leave `search.py` and the 1,006-line single-demonstration script as historical experimental paths. The new solver should not depend on their action-order controller or duplicate their report machinery. Make only narrow shared fixes if necessary. Do not start with mass deletion or another general framework.

Suggested new production surface: one `hwp_pareto.py` module for the finite library, restricted model, and frontier query, plus one small experiment entry point. Split the module only if distinct responsibilities actually become difficult to review. Reuse existing serialization and circuit emission.

## 3. Fix the input and execution contract

Start with two explicit input classes:

1. Native HWP layers: equal-angle phase rotations on distinct data wires.
2. The repository's parity-phase blocks: equal-angle predicates that may share data wires and require preparation.

Do not apply native-HWP workspace counts to materialized parity inputs. Annotate applicability on every library entry. Permit grouping only within a compatible normalized angle/coefficient class; preserve order across boundaries not known to commute.

The initial execution model remains deterministic unitary Clifford+T with clean scratch restored at every complete block boundary. No retained garbage or catalysts between blocks. This restriction makes composition and reuse tractable.

Keep measurement-assisted cleanup, dirty workspace, and catalysis outside the first solver model, while documenting them as relevant alternative assumptions. Do not claim a competitive frontier against those methods while omitting them.

Fix an error allocation before solving. One simple reproducible policy assigns each normalized term epsilon/N and gives a block covering k terms an allowance k*epsilon/N. Distribute that allowance among its actual synthesized rotations. A selected partition then has total allowance at most epsilon. Keep angles and tolerances in the library cache key. Freeze the synthesis seed/backend version. Do not mix circuits built under inconsistent error allocations or count errors of discarded alternatives.

## 4. Milestone A — executable prior-work library

Create a short construction audit before adding solver logic. For every entry record the source, implemented variant, applicability, cleanup model, parameter domain, emitted circuit, approximation bound, wire interface, T-count, measured T-depth, and scratch count.

Initial executable choices:

- Direct single-predicate implementation.
- Ordinary HWP on eligible input wires in place.
- Copied-parity HWP where direct input use is not supported.
- Multiple batch sizes using the same audited arithmetic.

These choices suffice to validate the optimization machinery; they do not cover all published HWP constructions. Kivlichan Appendix A.2 also gives limited-ancilla batching and a different accumulation scheme using roughly square-root workspace. Audit whether adapting that accumulation scheme to our unitary model provides a genuinely different library option. Implement it only with explicit unitary cleanup costs and a reproducible source mapping. The published measured-cleanup costs cannot be imported unchanged. [HWP constructions](https://arxiv.org/html/1902.10673v4)

Before a broad claim about published-method frontiers, include applicable competing families or narrow the claim explicitly. Catalyzed HWP depends on catalyst preparation and reuse; it belongs to a later execution profile unless implemented faithfully. [Kan–Symons](https://www.nature.com/articles/s41534-025-01091-0)

For tiny inputs, enumerate all nonempty compatible term subsets as eligible blocks. Record the maximum batch size and every pruning restriction. Do not silently restrict to contiguous terms and call the result globally exact. For native identical inputs, symmetry reduction may replace equivalent subsets only after justifying that wire interactions and interfaces remain equivalent.

Optional exact block optimization may occur once while building the library, with the same pass choices for every baseline. Retain each useful interface-compatible variant. Never claim that a scalar Toffoli count is its final T-cost.

**Gate A:** a small inspectable library emits valid circuits and reproduces the base constructions. Publish the library's coverage and omissions. No large backend-integration project is required to validate the model.

## 5. Milestone B — a deliberately restricted exact model

Begin with execution in nonoverlapping waves. A wave contains complete blocks with disjoint data-wire footprints and separate scratch. Every block returns scratch clean. All blocks in one wave finish before the next begins.

This is conservative: it forbids some interleaving and commuting transformations, but gives an explicit realizable schedule. Do not model it as unrestricted circuit scheduling.

For eligible block option j, store covered term set S_j, data footprint Q_j, T-count t_j, block T-depth d_j, and scratch requirement a_j. Binary choices x_j satisfy exact coverage:

    sum(x_j for j containing term i) = 1, for every term i.

Each selected block appears in exactly one wave. Within a wave, selected data footprints must be disjoint and scratch requirements must sum to at most A_max. For a wave W define:

    t(W) = sum(t_j for j in W)
    d(W) = max(d_j for j in W)
    a(W) = sum(a_j for j in W)

For the ordered wave plan:

    T_model = sum(t(W))
    D_model = sum(d(W))
    A_model = max(a(W))

The model reserves each block's footprint and scratch for the full wave. Clifford operations follow the existing logical T-depth convention; do not interpret these durations as physical clock time. Emit the chosen wave schedule explicitly. If the ordinary gate scheduler finds a smaller depth after removing wave barriers, report both values.

### Small exact solver

Use Pareto-label dynamic programming over the set of remaining terms. Each transition selects a legal wave covering a nonempty subset. Combine labels by sum for T and D and max for A. Store reconstruction pointers to circuits and wire mappings. Initially cap inputs at roughly 8-12 terms; measure the actual state growth before increasing the cap.

Because all blocks return the same logical data interface and clean scratch, future modeled choices depend on the remaining terms and resource label. This is the condition that makes dominance pruning sound here. Do not extend this pruning rule to retained intermediate values, differing output bases, or later joint-resynthesis outcomes without extending the state.

Validate against an independent brute-force partition/wave enumerator on cases with at most six terms. Treat this enumerator as a small test oracle, not another production solver.

If dynamic programming becomes the bottleneck, encode this same model using OR-Tools CP-SAT. Do not implement both engines initially. Report `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, and timeouts correctly; retain lower bounds and gaps when available. A timeout is not infeasibility. [CP-SAT status semantics](https://developers.google.com/optimization/cp/cp_solver)

**Gate B:** solver results agree with tiny exhaustive enumeration; every selected plan emits a valid complete circuit. Exactness means exact within this finite library, fixed precision policy, and wave model.

## 6. Frontier generation and user queries

Expose two operations using the same solved model:

- `solve(instance, A_max, D_max)`: minimum modeled T-count with depth and ancilla tie-breaks; return circuit and solver status.
- `frontier(instance, resource_ranges)`: nondominated resource labels with reconstructible circuits.

For the initial dynamic program, retain its nondominated labels directly. For a constrained solver, use epsilon-constraint queries: fix ancilla and depth bounds and minimize T. Sweep integer ranges or use safe bound-skipping; a coarse sweep gives sampled points, not a complete frontier. [Epsilon-constraint example](https://www.gams.com/latest/gamslib_ml/libhtml/gamslib_epscmmip.html)

Do not fill gaps by convex interpolation. A convex combination of resource tuples does not generally produce a valid deterministic circuit.

Keep three result labels separate:

1. **Model frontier:** exact or approximate within the stated construction/scheduling model.
2. **Emitted frontier:** nondominated results after measuring actual emitted circuits.
3. **Post-optimization frontier:** those circuits after a common gate-level optimization opportunity.

Model-dominated plans may become attractive after joint optimization. Consequently, pruning them does not justify a post-optimization optimality claim. On the smallest cases, optionally evaluate all plans to measure this discrepancy; otherwise state that the final frontier is a candidate set.

## 7. Milestone C — fair comparisons and an explanatory witness

Freeze a small manifest before looking for wins:

- Homogeneous native HWP layers at several sizes, including nonpowers of two.
- Two heterogeneous compatible groups, with different sizes or angles, to test resource sharing.
- One overlapping parity workload and one current QED-C phase block.
- A distinct-angle negative control with little grouping opportunity.

Use the same angle bindings, synthesis precision policy, wire model, library, and cleanup assumptions throughout. Start with a small grid of ancilla caps and reachable depth limits; report infeasible points and no-gain cases. Do not tune coefficients or retain only cases with a favorable mixture.

Required baselines:

1. Direct synthesis, including its naturally parallel schedule.
2. Best uniform construction/global batch cap, sweeping every applicable cap and handling remainder batches fairly.
3. Best per-group construction and batch choices, combined under the same workspace and wave restrictions. This stronger baseline separates grouping/scheduling gains from merely choosing a different method for each group.
4. The base repository's HWP plus common fixed downstream optimization.
5. Additional published construction families when implemented under matching assumptions.

Compute the union of feasible baseline points and remove dominated points. Compare the proposed method against that union. Give every construction the same downstream optimization opportunity; also retain pre-optimization results so the source of a gain is clear.

The explanatory witness must show term partition, chosen implementations, wave schedule, scratch mapping, model resources, emitted resources, and the strongest reference. If gains disappear under unrestricted baseline scheduling or common resynthesis, report that limitation.

For one query, calculate the benefit under the actual requested constraints. Do not require simultaneous improvement of all three metrics. A new point is a tradeoff improvement only relative to the comparator's attainable set; beating one arbitrarily chosen baseline is insufficient.

Record library-generation time, exact-search time, memory, and final optimization time separately. Use reproducible caches and equal evaluation settings. Report when the exact model stops scaling. Do not train or design a heuristic until exact solutions reveal a useful regularity.

**Gate C:** either produce a verified point outside the combined uniform/per-group reference frontier with a structural explanation, or conclude that this library/model gives no useful advantage on the fixed study. Both complete the experiment.

## 8. Verification and repository size

Keep the existing primitive and emitted-stream correctness checks. Add only tests for exact coverage, resource limits, interface-preserving composition, scratch reuse across waves, error allocation, solver reconstruction, tiny exhaustive agreement, and infeasible/timeout reporting.

Validate small complete circuits against their semantic target, including clean output scratch. For larger plans, use supported compositional checks and be explicit about their assumptions. Reuse independent checks; avoid a second serialization or replay framework.

Deliver:

- `docs/hwp-pareto-model.md`: short mathematical model, scope, and source audit.
- `src/collective_phase/hwp_pareto.py`: the focused implementation.
- `configs/hwp-pareto-study.yaml` and a small existing-style runner.
- `tests/test_hwp_pareto.py`: the meaningful model/circuit regressions.
- `reports/hwp-pareto-study.md`: frontier table/plot, one witness, limits and decision.
- Actual emitted circuits and compact raw records in existing artifact formats.

Aim for four reviewable commits: model/library; exact solver plus emission; comparisons; explanatory report and consolidation. Avoid new dashboards, generic plugin systems, and large snapshots of every solver state.

## 9. Future resource extensions: preserve an opening, do not implement them now

Store applicability and boundary assumptions explicitly so future models can add resources correctly. Clean/dirty qubits are different resources; catalysts are persistent states; magic-state supply is a time-dependent production/consumption constraint; measurement/feedforward has latency and stochastic considerations. These cannot be represented faithfully by adding arbitrary weights to the present triple.

A future model with retained intermediate results may need reversible pebbling or constraint-based scheduling. Existing SAT-based quantum memory work provides a predecessor, not a novelty claim for this project. [Reversible pebbling](https://arxiv.org/abs/1904.02121)

Stop the initial implementation at restored block boundaries and the wave model. Add one further resource only after a measured limitation motivates it.

## 10. Research and product stopping points

| Result | Interpretation and next step |
| --- | --- |
| Exact model matches uniform/per-group baselines | The modeled choices do not justify a new heuristic; inspect missing constructions or stop this direction |
| Mixed plans help only because a baseline implementation was poor | Fix the baseline; do not claim synthesis novelty |
| Mixed plans reliably improve constrained solutions | Explain the interaction, check prior art, and test fresh instances |
| Exact solutions help but scale poorly | Design one heuristic from the observed structure; benchmark against exact optima and gaps |
| Improvement vanishes after gate-level optimization | The high-level model needs refinement; do not claim the modeled gain as a final-circuit gain |

The first usable product is a small compiler query: input phase block plus limits in, verified circuit plus resources and model-relative guarantee out. The scientific contribution, if demonstrated, is the construction/resource interaction that produces better solutions—not the presence of an optimizer or a Pareto plot.
