# Adaptive resource tradeoffs: implementation handoff

Date: 2026-09-09

Repository: `gcc-bug/t-tradeoff`

Reviewed base: `remediation/t-tradeoff-m2r` at `828fb06d4123184a695e1bfc4a5f132c41abcd37`.

Implementation branch: `research/adaptive-tradeoff`. Start from the reviewed base; the initial commit on this branch contains this plan only. Keep implementation commits on this branch and leave the source branch unchanged. If the branch already contains implementation when this handoff is used, inspect its diff and continue that work rather than resetting it. Read any applicable `AGENTS.md` before editing. Preserve unrelated local changes.

## 1. Outcome and research question

Build a small, inspectable experiment in which **the final user objective stays fixed, while optimization priorities can change with the current circuit and region**. Reuse established optimization methods to supply transformations. Compare adaptive use of those transformations with strong static policies under matching compilation budgets.

The user cares about T-count `T`, scheduled T-depth `D`, and peak additional logical qubits `A`. These resources must influence which transformations are attempted during compilation, not merely which already-generated circuit is selected at the end.

Research hypothesis, not a novelty claim:

> Circuit-dependent changes in transformation priorities can reach a better final resource balance than fixed preferences or fixed pass order, because one transformation can change the usefulness of another.

A qualifying mechanism might release workspace that enables a subsequent depth reduction, or alter a phase representation so an existing synthesis method becomes useful. Dynamic weights, a portfolio of existing tools, and ancilla-budget enumeration are not sufficient contributions by themselves. Identify an actual circuit mechanism and audit its nearest prior work.

Success has two distinct meanings:

- Engineering success: a compact implementation, working external adapters, meaningful resource alternatives, consistent comparison, and an explainable trace.
- Research success: a specific adaptive decision mechanism improves complete circuits beyond budget-matched static alternatives on independently selected inputs. No success claim is required if the evidence is negative.

Do not build a general compiler framework, another rule catalogue, a new symbolic prover, or a new gate-synthesis engine. Do not expand the problem to noncommuting programs merely to make one baseline applicable.

## 2. What the current branch actually contains

The default study compares `independent`, a local greedy `shared_parity`, and `hwp_adder_unitary`. The latter emits staged compressors but reverses their arithmetic using exact 7-T Toffolis. It searches balanced batches under batch-size caps. The dependent-triple rewrite is disabled by default. Relational analysis, NCF, and an external T-count/depth optimizer are not integrated.

The seven development cases are four explanatory/control inputs and three checksum-pinned QED-C graphs of 4, 6, and 8 vertices. The current settings are angle `0.173`, total error `1e-4`, workspace budget 8, and T-count-first selection. These graphs are development data, not held-out evidence.

Concrete cleanup targets from the reviewed tree:

| File | Observed responsibility / issue | Required direction |
| --- | --- | --- |
| `experiments.py` (69,577 bytes) | Execution, history, replay, reporting, evidence labels | Retain a short experiment driver; remove historical dispatch and duplicate report paths |
| `reporting.py` (12,894 bytes) | A second substantial reporting path | One comparison table and one decision trace renderer |
| `selection.py` (12,177 bytes) | Evaluates/lower/verifies all alternatives, selects by fixed objective, serializes artifacts | Separate the small fixed final objective from adaptive search; reuse evaluated states |
| `baselines/hwp.py` (19,657 bytes) | Active adder implementation mixed with ANF and legacy macros | Keep the emitted adder construction and direct fallback only in production |
| `baselines/catalyzed_hwp.py`, `candidates/dependent_triples.py` | Unverified estimate and retired diagnostic algorithm | Remove from production and default imports; preserve useful facts in documentation/fixtures |
| `resources.py` | Counts emitted stream; workspace comes from declared candidate width | Preserve gate counting; add only the schedule/lifetime information required by actual actions |
| `verification/lowered.py` | Existing primitive-binding verification | Keep the real mutation regression; adapt the check boundary for externally resynthesized gates |
| `tests/test_experiments.py` | Extensive artifact replay; duplicated `test_replay_rejects_mutated_total_global_phase_token` definition | Consolidate essential tests; remove duplicate and historical-format obligations |

File sizes identify review burden, not a deletion quota. Delete obsolete behavior before introducing additional abstractions. Do not split one large file into many pass-through modules and call that cleanup.

## 3. Fixed final objective and changing local preferences

### 3.1 Final contract

Retain the diagonal affine-parity target and its current global-phase convention:

`U(theta)|x> = exp(i * theta * sum_j p_j(x)) |x>`.

Keep angle multiplicity, exact-angle handling, block boundaries, clean-workspace restoration, and little-endian wire semantics. Use the same full-workload approximation budget for every competitor. Initial experiments remain unitary Clifford+T.

Support two compact final-objective modes using one shared evaluator:

1. Constrained single metric: minimize one of `T`, `D`, `A` with explicit upper limits on the others. Ancilla-first requires meaningful T/depth targets for these zero-extra-qubit direct-synthesis inputs.
2. User balance: minimize `J = wT*T/Tref + wD*D/Dref + wA*A/Aref` under hard limits. Weights are nonnegative, not all zero. Reference scales are positive and fixed from configuration or a common initial reference before any policy runs; never normalize by a zero reference ancilla count or changing best-so-far values.

The final objective and its tie-break rules are immutable during a run. Hard qubit and accuracy limits are never relaxed. In the first implementation, keep other declared hard limits valid for accepted search states too; permit temporary worsening of the objective only within those limits. An infeasible requested target returns an explicit status, not an altered limit.

For different device preferences, use separate runs with declared objective parameters. A hardware-derived runtime objective is an optional later adapter to a real resource estimator with explicit factory, code, timing, and error assumptions. Do not label a weighted logical score, `T*D*A`, or `max(T/rate, D*time)` as measured physical execution time.

### 3.2 Local priorities

The controller chooses both a region and an action family based on the current state. Priorities may differ across regions and iterations.

| State evidence | Prioritize | Required contextual check |
| --- | --- | --- |
| Region lies on a T-critical dependency path | Depth-oriented resynthesis | Does the complete circuit's critical path actually shorten? |
| A useful alternative cannot fit available workspace | Workspace release/reuse alternative | Is there a real compatible follow-up that uses the released workspace? |
| Region has sufficient scheduling slack | Count-oriented simplification/resynthesis | Does its extra depth remain inside actual slack? |
| A representation change creates a supported algebraic opportunity | Relevant existing symbolic/synthesis method | Does it improve the fixed final objective after lowering? |

Nearness to a limit is not by itself evidence that a transformation will help. Use candidate effects and schedule information. Adding a CLI option that changes only the final selection is not completion of this task.

## 4. Start from existing methods, with a bounded integration scope

Integrate a small number of real backends first. A citation, metadata label, or homemade stand-in does not constitute reuse of a method.

| Method | Required role | Initial scope |
| --- | --- | --- |
| Amy–Lunderville relational analysis | Phase folding using linear/nonlinear relations | First integration target; locate the paper artifact/revision, not just a generic tool with the same name |
| T-par / ancilla-assisted depth resynthesis | Existing depth/workspace alternatives | First depth-backend target; inspect actual supported options and output ancillas |
| PyZX / supported phase-polynomial optimization | Joint optimization across decomposition boundaries | Use one pinned established backend; Feynman functionality may cover this role if demonstrated |
| NCF / Trasyn | Structured joint synthesis at the Pauli/rotation level | Perform a bounded applicability/artifact probe before implementing an adapter |
| Existing emitted ordinary HWP | High-level collective alternative | Keep, optimize its lowered output fairly, and label unitary cleanup accurately |

The Feynman repository exposes optimization and verification tools and cites T-par. The relational-analysis paper has its own artifact; do not assume all its functionality is in the repository's default branch. Pin the actual revision, license, command/API, supported inputs, precision semantics, and ancilla contract for each integrated method.

For NCF, determine whether useful groups actually occur in our commuting diagonal workloads. Clifford conjugation preserves the rank of independent Pauli generators, so general commuting groups do not automatically collapse to a single-qubit synthesis problem. The paper's two-qubit precision/runtime limitations must not be hidden by relaxing our error budget. If a compatible implementation or useful grouping is unavailable, record the concrete reason and continue the supported experiment. A blocker is not evidence that NCF loses.

Prefer thin subprocess/API adapters to copied algorithms. Inspect the backend's advertised interface; do not invent command-line flags. Time-box the initial build/applicability probe per backend to one working session, then report an unresolved blocker rather than writing a replacement engine. Complete other independent work.

Before building adaptive search, demonstrate on real emitted circuits:

- at least one existing T-count-oriented transformation beyond the current triple rule;
- at least one existing depth-oriented transformation;
- at least one legal alternative that changes allocated workspace or its reuse;
- at least two non-equivalent resource alternatives, with an explained tradeoff.

One backend can satisfy multiple requirements. If all adapters produce one effective circuit, a three-resource adaptive controller is not yet justified. Do not manufacture a tradeoff by padding gates or ancillas.

## 5. Preserve structure and evaluate real lowered circuits

Keep the symbolic source representation together with each region's current implementation. An external optimizer may replace a region's emitted circuit while the region retains its original verified semantic target. Do not attempt to reverse-engineer every optimized gate stream back into an arithmetic program.

Begin with closed regions whose interface is explicit: same logical data wires, declared clean workspace, restored workspace, and preserved unitary under the phase convention. Optimize across Toffoli and rotation decomposition boundaries inside a region. Use a small surrounding region when boundary cancellation matters. Carrying live intermediate values across region boundaries is deferred until a concrete example requires it.

Each evaluated state needs only:

- source target and current region implementations;
- emitted gates and wire mapping;
- whole-circuit `T`, scheduled `D`, and actual allocated peak `A`;
- dependencies and the limited workspace lifetime information needed for proposals;
- approximation/equivalence status, parent action, and final objective value.

Measure the final optimized gate stream. `7 * Toffoli_count` remains a pre-optimization diagnostic, never the final cost objective. Recompute T-depth after the transformation using actual dependencies; do not sum local depths. Ancilla-free arithmetic inputs, carry registers, and borrowed wires must not be conflated.

Only credit released workspace when the register is restored and the emitted allocation actually reuses it. A smaller declared metadata number is not a valid reduction. Track peak live logical workspace and allocated physical wire slots consistently; report the implemented allocation as the constrained resource.

After cross-boundary optimization, T gates may no longer have a unique arithmetic-versus-rotation origin. Report pre-optimization component counts separately and post-optimization total T. Do not preserve the current subtraction formula if it produces misleading attribution.

Cache exact repeated backend requests using target/region identity, boundary contract, backend revision/options, angle values, tolerance, and workspace assumptions. Context-dependent full-circuit costs are recomputed after splicing, not reused from a local cache.

## 6. Minimal adaptive controller

### 6.1 First implementation

Use a transparent deterministic controller before considering learning, reinforcement learning, or a large portfolio. Reuse the same proposal/action pool for all policy comparisons.

1. Start from a declared common circuit and a small shared set of existing construction seeds, charged identically across policies.
2. Inspect T-critical regions, slack, and workspace conflicts that prevent supported actions.
3. Rank a bounded set of region/action proposals. Use a simple documented priority rule tied to the final objective and actual constraint pressure. This first rule is an experimental baseline, not a claimed novel algorithm.
4. Evaluate only the highest-priority few proposals using existing backends; splice and recount the complete circuit.
5. Accept an improvement under the fixed final objective. If no one-step improvement exists, allow one bounded two-action attempt with a specific predicted enabling relation.
6. Commit the two-action sequence only if its checked endpoint improves the final objective and both intermediate/end states satisfy hard limits; otherwise retain the original state.
7. Update the bottleneck information and repeat until the shared evaluation/time budget is exhausted or no supported improvement remains.

Use fixed deterministic tie-breaks. Maintain a best feasible incumbent throughout. The search can inspect a temporarily inferior state during lookahead; the final result is always the best accepted state under the fixed objective.

Starting engineering limits, tunable only on development data: beam width at most 2 if a beam is needed, lookahead at most 2 actions, at most 4 fully evaluated proposals per iteration, and an explicit total backend-time/call budget. These are limits on implementation size and compute use, not claims about optimal parameters. Avoid building a beam abstraction if one incumbent plus a provisional lookahead state suffices.

### 6.2 Important distinction: search versus reporting

Keep a Pareto archive of evaluated complete circuits for reporting, but do not let immediate metric dominance automatically delete provisional search states. A dominated intermediate can expose a useful next transformation. Local dominance is even less conclusive when boundary implementations differ.

The scalar dynamic score may rank proposals; it must not replace the fixed final evaluator or silently allow an inferior final answer. Any adaptive weight formula must use fixed normalization scales, document its inputs, and be tested against static use of the same formula.

### 6.3 One concise decision trace

Record one row per accepted action or provisional two-action sequence:

`step, region, action/backend, reason, local_priority, T_before/after, D_before/after, A_before/after, J_before/after, evaluations, backend_seconds`.

For a two-step sequence, show the provisional regression and the final improvement explicitly. Keep best-so-far and current/provisional values distinct. Rejections need counts and a small set of reason codes, not full recursive artifacts for every proposal.

## 7. Correctness and approximation: retain essential checks only

Reuse existing verification and external equivalence tools; do not expand verification into the main research product.

- Keep shared target semantics, clean-ancilla restoration, wire/angle conversion checks, and representative primitive correctness tests.
- Keep the forced-compositional-mode T-to-T-dagger mutation regression. The prior bug was real and should not return during cleanup.
- An externally optimized event stream no longer matches the old primitive event template. Do not mark it invalid solely for that difference, and do not attach the old certificate to it. Check equivalence between the pre/post optimization region using an applicable existing checker, or a small independent matrix/isometry check, then compose that evidence with the original target-to-circuit error bound.
- If the external operation is exact, it adds no approximation error after equivalence is established. If it resynthesizes approximately, charge its certified error. Repeated approximate actions must not each reuse the full error budget. Prefer exact optimization after one controlled approximate synthesis stage in the first version.
- If a high-level region is resynthesized from its original exact target, replace its prior error contribution rather than double-counting or forgetting it. Predeclare a conservative per-region budget within the whole-circuit budget; repartitioning requires explicit reallocation and invalidation of affected cached evaluations.
- Unknown/timeout verification is inconclusive. Such an output does not become the selected certified result. Small dense checks should be size/memory bounded; sampled checks are diagnostics, not operator-norm certificates.

Default test responsibilities should fit into a small number of focused groups:

| Keep/consolidate | Concrete failure covered |
| --- | --- |
| Semantics + preprocessing | Wrong parity, coefficient, constant phase, wire order |
| Active HWP arithmetic | Wrong compressor, non-power-of-two weight, missing inverse cleanup |
| Lowering + adapter integration | Wrong gate conversion, invalid optimizer output, wrong error contract |
| Resources + final policy | False depth savings off the critical path, fake ancilla release, hard-limit violation |
| Adaptive trace | A small actual circuit permits an enabling two-action sequence; mock policy fixtures test mechanics only |
| One default end-to-end study | Runnable CLI/config, measured rows, final selection and report consistency |

Delete tests solely for removed ANF counts, legacy macro rankings, retired triple wrappers, old schema-v1 report compatibility, and exact historical prose. Keep at most one relevant stored-result consistency test if stored results remain a supported input. Remove duplicate test definitions; do not delete meaningful regressions merely to reduce test count.

Run the existing suite once before cleanup when dependencies permit, record failures, and test the affected behavior after each commit. Do not repeatedly run every historical experiment or add broad property-test frameworks for this refactor.

## 8. Cleanup and module responsibilities

Keep the current package and meaningful file names. Suggested responsibility map (not a demand for a new framework):

- `ir.py`, `preprocessing.py`: target and shared normalization.
- `baselines/independent.py`, `shared_parity.py`, `hwp.py`, `arithmetic.py`: active constructions; keep the greedy parity method explicitly a basic reference.
- `adapters/`: only thin wrappers for integrated external backends.
- `lowering/`, `resources.py`, `verification/`: shared numerical/gate boundary.
- `selection.py`: fixed objective, limits, and final Pareto reporting; remove duplicate lowering of previously evaluated states.
- `search.py`: small adaptive/static policy loop; action logic stays with the construction/backend that owns it.
- `experiments.py`, `reporting.py`, `cli.py`: one execution path, one results format, one report.

Remove the active production implementation of the legacy HWP macro, catalytic estimates, ANF reference, and dependent-triple optimizer after checking imports with `rg`. Retain the dependent-triple input as a useful small semantic fixture. Keep the audit's analytical equivalence statement without an algorithm wrapper pretending to be an independent competitor.

Delete unused imports, aliases such as the legacy `compile_hwp` route, obsolete CLI methods, and macro-only result fields once references are removed. Keep just the current study, a smoke configuration, and the adaptive comparison configuration; remove historical pilot configs from the active workflow. Git history and the base branch preserve them.

Keep historical reports unchanged in content and clearly indexed as historical; they need no runtime replay support. Consolidate duplicated planning/progress documents into the review guide and one current methodology document, retaining source citations and the HWP implementation audit. Do not duplicate retired code into an `archive/` package.

Review targets: the main experiment driver and search loop should each be readable in one sitting (aim for roughly 300–400 substantive lines per file); functions should have one clear responsibility. These are review prompts, not hard quotas. Report before/after production LOC, test LOC, and active module count, with explanations for additions. A smaller README is not evidence of a smaller system.

## 9. Fair experimental comparison

Separate two questions:

### A. Does the adaptive controller add value?

Use the same initial seeds, actions, adapter versions, tolerances, region availability, and final objective for:

1. Fixed T-oriented, depth-oriented, and ancilla-oriented policies.
2. A small predeclared set of static normalized weight vectors; select their best endpoint under the user's final objective.
3. A sensible fixed pass order using the same methods.
4. Adaptive priorities without lookahead.
5. Adaptive priorities with bounded lookahead.

Split one total budget across the static multi-start runs when comparing against one adaptive run. Charge startup/shared seeds consistently; record candidate evaluations, uncached synthesis calls, and wall-clock backend time. Timeouts and shared-cache advantages must not be hidden. If fixed orders are tuned, tune them only on development cases and charge/report the tuning budget.

The comparison must reveal whether gains come from adaptive priority, extra calls, lookahead alone, or importing stronger primitives. Add a fixed-priority controller with the same lookahead when lookahead appears to explain the result.

### B. Is the final construction competitive with prior work?

Run applicable external methods in their native recommended configuration as well as through our adapter, preserving assumptions. Compare against the union of their feasible complete-circuit results. Report any subset reimplementation accurately. Measured and catalytic constructions remain outside the initial unitary ranking, with that scope restriction explicit; do not claim superiority over them.

All default unitary constructions get the same opportunity for downstream joint optimization. No baseline is forced to retain independent 7-T Toffoli expansions while the adaptive method receives optimization across them.

### Workloads

- Retain the current seven cases as regression/development cases, including the weighted negative control. They are not enough for general research claims.
- Use small controlled examples to explain a mechanism. Show one where adaptation helps and one where it is neutral/unhelpful if such cases occur; do not invent an effect for symmetry.
- Before tuning the controller, freeze a modest second manifest from QED-C graphs not used in development, selected by declared size/degree rules and fixed file ordering. A reasonable initial target is roughly 8–12 cases spanning larger sizes; exact files must be resolved, pinned, and checked before runs. Select based on input properties, not observed wins.
- If that public subset is unavailable, use clearly labeled reproducible synthetic graphs with fixed sizes/seeds for scaling diagnosis. Do not call them public or held-out QED-C evidence. Keep weighted/no-dependence controls.
- Keep a single angle/error setting initially (`0.173`, `1e-4`) to make comparisons tractable. Only after a mechanism appears, test a second generic angle and a stricter precision on a small predeclared subset. Exact Clifford-angle cases are controls, not headline wins.

Do not add HamLib ingestion or a broad application suite during this milestone. Backend-native benchmark examples may validate adapter reproduction without silently broadening the `PhaseProgram` semantic contract.

### Required output

One short report should contain:

1. Actual integrated methods and unsupported cases.
2. Paired pre/post joint-optimization resource triples.
3. Final objective, feasibility, budgets, and outcomes for the policies above.
4. One readable step trace explaining why priorities changed.
5. A plot or table of `(T,D,A)` after accepted steps and final Pareto points; annotate provisional lookahead states separately.
6. A mechanism conclusion: what an existing method missed, or why no adaptive benefit was found.

Aggregate percentages must use matched feasible cases and show their denominator. Unsupported, timed-out, and verification-inconclusive cases are separate statuses, not wins or infinite-cost baselines.

## 10. Commit order and acceptance gates

| Commit / milestone | Concrete deliverable | Acceptance criterion |
| --- | --- | --- |
| 1. Simplify active workbench | Remove dead methods/aliases/tests; one runner and report path | Active semantic/resource results preserved on the small regression study; no required adapter work hidden in cleanup |
| 2. Integrate existing optimization | Working pinned count/relational and depth/workspace adapters; NCF applicability note | Real emitted alternatives with verified semantics and genuine resource differences; documented sources and limits |
| 3. Establish static reference | Optimize direct/HWP fairly; fixed final objective; actual resource/schedule accounting | Explain pre/post costs and reproduce a static comparison without adaptive search |
| 4. Add adaptive priorities | Small transparent controller, immutable final objective, concise trace | State-dependent decisions change actual proposed transformations; best incumbent and hard limits preserved |
| 5. Add bounded enabling moves | At most two-action lookahead and matched fixed-policy ablation | A real circuit example is checked, or the report explicitly finds no useful sequence; no claims from mocks |
| 6. Evaluate and document | Frozen comparison manifest, budget-matched report, updated review guide | Explain gains/losses, scope limits, code reduction, and research decision |

Proceed through authorized implementation steps without repeatedly requesting routine approval. Gates establish whether later scientific claims are supported; they do not require fabricated positive findings. If a backend cannot be obtained or supported resource alternatives do not exist, finish cleanup, available adapters, and the bounded diagnosis, and state exactly what remains blocked. Do not compensate by expanding verification or adding new rules.

Keep each commit focused. Push this implementation branch when the work is ready; do not merge into the source branch. The implementation handoff should list the final commit, commands run, any concrete skipped checks, before/after code size, and one example's result. No claims of improved circuits before running the comparison.

## 11. Sources and provenance

Repository facts are grounded in the reviewed commit; experiments were not rerun while writing this plan.

- [Base commit](https://github.com/gcc-bug/t-tradeoff/commit/828fb06d4123184a695e1bfc4a5f132c41abcd37)
- [Current study configuration](https://github.com/gcc-bug/t-tradeoff/blob/828fb06d4123184a695e1bfc4a5f132c41abcd37/configs/default-study.yaml)
- [Current report](https://github.com/gcc-bug/t-tradeoff/blob/828fb06d4123184a695e1bfc4a5f132c41abcd37/reports/default-study.md)
- [HWP audit](https://github.com/gcc-bug/t-tradeoff/blob/828fb06d4123184a695e1bfc4a5f132c41abcd37/docs/hwp-implementation-audit.md)
- [Amy–Lunderville: Linear and non-linear relational analyses](https://arxiv.org/abs/2410.23493), [paper artifact](https://doi.org/10.5281/zenodo.13921830), [Feynman toolkit](https://github.com/meamy/feynman)
- [Amy–Maslov–Mosca: T-depth optimization via matroid partitioning](https://arxiv.org/abs/1303.2042)
- [Li et al.: Non-Clifford Fusion](https://arxiv.org/abs/2510.13573)
- [Reducing T Gates with Unitary Synthesis / Trasyn](https://arxiv.org/html/2503.15843v2)
- [Vandaele: Lower T-count with faster algorithms](https://quantum-journal.org/papers/q-2025-09-16-1860/)
- [PyZX implementation](https://github.com/zxcalc/pyzx)
- [GUOQ: Optimizing Quantum Circuits, Fast and Slow](https://arxiv.org/abs/2411.04104)
- [AlphaTensor-Quantum](https://arxiv.org/abs/2402.14396)

These references establish relevant prior approaches, not that the proposed adaptive policy is novel or that every current release exposes the adapter interface we need. Verify exact backend revisions during implementation. This handoff supersedes earlier expansion plans where they conflict with its adaptive objective and cleanup scope.
