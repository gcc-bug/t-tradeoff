# Test plan: cost-directed HWP synthesis using existing circuits and certified bounds

Date: 2026-09-20

## 1. Decision and intended result

Continue in the same repository. Implement this experiment on a new branch, `research/hwp-guided-search`, based on the actual `research/hwp-pareto-synthesis` implementation. Preserve the exact Pareto solver as a small-instance reference.

The next deliverable is one inspectable experiment answering:

> Given a phase block, a linear resource cost, resource limits, and previously computed circuits, can we find a good circuit and certify its remaining model-relative cost gap faster than computing the complete frontier?

Distinguish two hypotheses:

- **H1 — search efficiency:** previous feasible circuits, valid bounds, and cost-directed exploration reduce work needed to reach a given cost gap within the same construction model.
- **H2 — construction quality:** a specified additional construction family produces better cost values than the combined established reference families.

H1 does not imply H2. A faster search over an unchanged complete model cannot improve that model's optimum. Do not describe an additional nondominated point as a linear-cost improvement unless it actually wins a corresponding cost query.

The first milestone tests H1 and diagnoses whether the current library has room for H2. It does not implement a general compiler, an unrestricted synthesis oracle, or a complete branch-and-price framework.

## 2. Establish the real implementation base

As checked on 2026-09-20, remote `research/ancilla-iterative` is at `8534292ec666ab1375b6c2381be88fd1d70e06b4`. It contains evidence snapshots but not `src/collective_phase/hwp_pareto.py` or `scripts/run_hwp_pareto.py`. The evidence names a separate worktree and revision `47d71a791413a85776cdf9f517a6a237b3e510d5`; that revision was not accessible remotely during review.

Local Codex must first:

1. Inspect git status, worktrees, branch heads, and applicable AGENTS.md. Preserve unrelated changes.
2. Locate the real Pareto implementation and compare its source fingerprint with the study. Record any later changes rather than resetting to an old snapshot.
3. Read its solver, reconstruction, baseline generation, tests, and timeout handling. Confirm the documented model against code.
4. Create the new branch from that implementation's recorded clean commit, or reuse an existing branch without resetting it. Do not base new solver work on the evidence-only branch or reconstruct the missing implementation from prose.
5. Keep the implementation and results reviewable together. Push only according to existing user authorization and repository policy; do not publish private ARA or anonymous research artifacts as part of this task.

If the source is genuinely unavailable, report that precise blocker. The experiment requires the existing solver; duplicating it would add unnecessary code and weaken the comparison.

## 3. Freeze the model and the meaning of a guarantee

Reuse the current phase semantics, normalized-term precision allocation, direct/in-place/copied HWP options, emitted Clifford+T costs, and clean ancillas restored at complete-block boundaries. Reuse the complete-wave scheduling model and original block boundaries.

Every guarantee must carry a model fingerprint covering input, constructors, batch cap, precision policy, synthesis version/seed, wave rules, ancilla semantics, and hard constraints.

For an executable circuit C, use r(C) = (T, D, A), where D is wave T-depth for the certified model objective. Also report ordinary emitted scheduled depth separately. Define:

    J_w(C) = w_T T(C) + w_D D(C) + w_A A(C)

Weights are nonnegative rational numbers, not all zero. Parse decimal configuration values exactly and scale to integer arithmetic where possible. Hard ancilla/depth limits remain separate feasibility conditions.

For comparisons of preferences, freeze scales before search: s_T=max(1,T_direct), s_D=max(1,D_direct), and s_A=max(1,A_envelope), where A_envelope is the study's declared maximum workspace. Effective weights are the user preference coefficients divided by these scales. Share scales across methods and hard-cap queries for the same input; a zero-ancilla direct circuit must not cause division by zero. Record both preference and effective rational coefficients. Never renormalize when a better circuit arrives.

The solver returns a feasible incumbent with cost U and a valid lower bound L such that:

    L <= optimum within the declared model <= U.

Report absolute gap U-L. If L>0, the quantity (U-L)/L certifies relative excess over the optimum; stop at tolerance eta when U <= (1+eta)L. Handle L=0 explicitly; do not report an unsupported percentage guarantee. Exact completion gives OPTIMAL; an interrupted run with an incumbent gives FEASIBLE with its bound. Distinguish TIMEOUT, proven INFEASIBLE, and numerical/verification failures.

These certificates do not cover constructions outside the model, arbitrary gate-level optimization, or physical runtime. All emitted circuits remain subject to the existing error and correctness contract.

## 4. First diagnose whether the current model improves linear costs

Before building the new search, query the existing exact frontiers and the combined reference sets using the same target costs and hard limits.

The retained overlapping_6 witness is (284,166,3). It improves constrained T-count at A<=3 and D<=200. However, the average of reference points (228,112,4) and (312,156,0) is (270,134,2), smaller in every coordinate. Thus this witness cannot strictly improve an unrestricted nonnegative linear cost over both references. This average is a geometric argument, not an executable circuit.

Keep that witness as a constrained regression. Do not use it as evidence of an unrestricted weighted-cost improvement.

Evaluate a frozen set of weights. If claiming that there is no strict weighted-cost improvement for *any* nonnegative weights, check it rather than inferring it from a sparse sweep. For each proposed point p and eligible reference set B, the small feasibility/LP diagnostic is:

    maximize delta
    subject to sum(w)=1, w>=0,
               w dot (b-p) >= delta for every b in B.

A positive optimum identifies a cost where p strictly beats every reference. Treat numerical values near zero as inconclusive unless certified. This is an optional small diagnostic, not another production search engine. For hard constraints, filter both sets by the same constraints before this check.

Output a short baseline table: input, cost/limits, best reference, exact model optimum, and improvement. If the current library offers no improvement on the chosen costs, H1 is still testable; label H2 as unestablished.

## 5. Implement one cost-directed search, reusing the existing model

Use best-first branch-and-bound over the existing remaining-term states and canonical complete-wave transitions. Do not implement CP-SAT, column generation, and a second dynamic program simultaneously.

Each node contains remaining terms R, a reconstructed prefix, prefix resources (T_p,D_p,A_p), and a valid completion lower bound. The current model's transition remains:

    T' = T_p + T_wave
    D' = D_p + D_wave
    A' = max(A_p, A_wave).

For a wave, add block T and scratch allocation, and take maximum block depth; require disjoint data footprints and the existing boundary rules. Reuse existing generation/reconstruction helpers after checking their contracts.

Seed U with the best feasible existing direct/uniform/per-group/reference circuit for this query. A known circuit is a feasible upper bound; its nondominated label is not an optimality certificate. Keep the reconstruction, not just its resource tuple. Return the seed immediately if no better verified circuit is found.

Pop the node with the lowest valid cost bound. Prune it if it cannot improve U or satisfy hard limits. Retain the existing safe dominance rule only for the same remaining terms and restored boundary interface. Resource dominance is not a valid pruning rule for arbitrary partially optimized gate streams.

Preserve deterministic tie-breaking and input order. The primary guarantee concerns cost. If equal-cost solutions are pruned, do not additionally claim optimal depth/ancilla tie-breaking; either implement lexicographic certification or explicitly report a deterministic cost-optimal representative.

### A simple, auditable first lower bound

Begin with the full precomputed option library to isolate search behavior from synthesis. For an option j, let S_j be its covered terms and (t_j,d_j,a_j) its costs. At a state, consider a superset of all options that could appear in a completion, contained in R and respecting immutable compatibility rules. Ignoring some scheduling/resource restrictions is a relaxation and is safe for a lower bound.

For each remaining term i define:

    pi_i = min over j containing i of t_j / |S_j|.
    L_T(R) = sum over i in R of pi_i.
    L_D(R) = max over i in R of min over j containing i of d_j.
    L_A(R) = max over i in R of min over j containing i of a_j.

Empty R has zero bounds. No covering option for a remaining term proves infeasibility within this library.

Justification: for every selected option j, sum(pi_i for i in S_j) <= t_j, so summing over an exact partition lower-bounds T. Every completion contains some block covering each term, hence its total wave depth and peak scratch are at least those individual minima. These bounds may be weak—particularly L_A when direct options exist—but they are interpretable.

The node cost bound is:

    w_T (T_p + L_T) + w_D (D_p + L_D)
      + w_A max(A_p, L_A).

Use exact rational arithmetic or conservatively certified rounding. Compare each bound against exact tiny completions in tests. Do not promote a heuristic estimate to a pruning bound.

Count full-library generation in end-to-end time. This initial experiment can demonstrate fewer explored plans, not avoidance of subset synthesis.

### Timeout accounting is part of correctness

Keep a valid bound for every unfinished subtree, including successors not yet generated when a deadline interrupts node expansion. Retaining the parent expansion as pending with its bound is sufficient. Do not drop an expansion and then compute L from only the remaining visible queue.

The global bound is the minimum of U and bounds covering all unresolved subtrees. Closed dominated/pruned states require sound justification. On a finished empty queue, the incumbent is optimal within the model. Test interruption during successor generation as well as between nodes.

## 6. Test reuse of previous optimality information

Add this after the basic search is correct, using the same search engine.

Separate the archive into:

- feasible circuits: used only to improve U;
- certified inequalities: weight vector v, lower bound b, model/feasibility fingerprint, and certification source, establishing v dot r >= b.

Only reuse inequalities over the same feasible model, or where an explicitly checked set inclusion makes reuse valid. A bound from a more restrictive resource problem generally cannot bound a broader one. A circuit from different constraints can be reevaluated for feasibility, independently of whether its old certificate transfers.

For a cheap exact transfer mechanism, combine archived bounds with nonnegative rational multipliers lambda_i satisfying:

    sum(lambda_i v_i) <= target w componentwise.

Since all resources are nonnegative, sum(lambda_i b_i) is a valid target-cost lower bound. Start with single-certificate scaling; use only a bounded small combination search if helpful. Any approximate LP used to propose multipliers must have its feasibility and bound checked conservatively before pruning.

Do not preload the target's exact answer or free certificates from a full frontier computation. Count the cost of acquiring seed circuits and certificates, or label them as an already available archive and additionally report amortized cost across the whole query sequence. Hold out target weights to measure useful transfer.

A full geometric outer-approximation controller is deferred. The experiment first tests whether these inexpensive reused bounds reduce the target query's actual work.

## 7. Evaluation and ablations

Use the existing nine cases as development inputs. Freeze additional inputs and costs before inspecting improvements: distinct native sizes, multiple equal-angle groups, and overlapping parity patterns generated with a recorded seed. Use the existing verifier's supported sizes; do not invent a scalable certificate to bypass its limits.

Development preferences in normalized (T,D,A) units:

    (1,0,0), (0,1,0),
    (0.8,0.1,0.1), (0.1,0.8,0.1), (0.1,0.1,0.8),
    (1/3,1/3,1/3).

Hold-out mixed preferences:

    (0.6,0.3,0.1), (0.2,0.5,0.3), (0.4,0.2,0.4).

Include both unrestricted queries within a declared maximum workspace envelope and hard-cap queries, including the overlapping_6 regression. Declare the envelope when saying unrestricted; it is not unlimited ancilla synthesis.

Compare:

| Method | Purpose |
|---|---|
| Existing exact frontier DP, then select | Ground truth and amortized many-query reference |
| Cost-directed search with direct seed and trivial bound | Search-order control |
| Same search with full reference seed pool | Effect of known feasible circuits |
| Same search plus structural completion bounds | Effect of valid pruning |
| Same search plus archived certified inequalities | Effect of cross-query mathematical information |

Keep seeds, library, legal transitions, objective, cache policy, and deadlines matched except for the intentionally varied component. An expensive baseline seed search is not free.

Measure end-to-end time, separate library/search/verification time, states expanded, waves generated, options synthesized, time to first improved U, time to 5% and 1% certified relative gap, final U/L/status, and model optimum where available. Time thresholds are examples of reporting targets, not promised achievable bounds.

Use repeated timing runs for tiny searches and avoid speedup claims from timer noise. Report cold startup and warm/many-query use separately. A frontier computed once can be very competitive across many weights; charge that computation once rather than once per query. Include unsuccessful attempts and all archive acquisition costs.

Run equal downstream optimization on a small matched set of finalists if needed for practical conclusions. Preserve both parent and verified child. The model certificate belongs to the modeled objective and does not automatically certify the post-optimization search space. Keep pre/post tables distinct.

## 8. Conditional next step: generate options on demand

Only proceed if measured library construction or option enumeration is a material bottleneck and H1 is promising. Do not make this a mandatory component of the first milestone.

Study column generation using the current exact library as an oracle on tiny cases:

1. Start from options used by existing feasible circuits.
2. Define a correct relaxed master problem covering terms and representing wave/scratch constraints. A block tuple alone is insufficient to represent peak workspace and depth.
3. Use dual information to request promising missing options or legal waves; compare requested options against the complete tiny library.
4. Reconstruct integer feasible circuits and check whether the requests actually improve U.

Important: a minimization LP restricted to only the generated columns is not automatically a lower bound on the full integer model. Missing columns may lower its value. Require exact pricing over the declared full family, or a rigorously justified correction, before treating it as a full-model bound. Failure of heuristic pricing is not a certificate that no useful option exists. Completing root LP pricing also does not prove the integer optimum; use valid integer search or report only the relaxation bound.

Reuse existing optimization software if this stage is justified. Do not write a general branch-and-price framework. This extension avoids exhaustive option generation only if its pricing problem is cheaper than generating all options; measure that cost explicitly.

## 9. Construction expansion is a separate gated experiment

If the exact current model has no weighted-cost advantage, a faster search cannot supply that missing advantage. Inspect the winning/near-winning circuit structures and choose one specific missing prior-work family to investigate.

The previously documented accumulation-based HWP construction is a candidate, not a mandatory choice. Its unitary arithmetic, cleanup, and applicability require their own audit. Measured or catalytic constructions change assumptions and require matched baselines; do not mix their formulas into the unitary library.

Add at most one justified family in a follow-up. Test whether it improves the combined reference cost for a frozen preference/constraint range. If not, report the negative result rather than expanding the framework again. The Pareto geometry directs effort; it does not prove a missing circuit construction exists.

## 10. Small implementation footprint and meaningful tests

Prefer these additions after inspecting actual APIs:

- `src/collective_phase/hwp_cost_search.py`: cost query, one search engine, bound functions, small certificate record.
- `tests/test_hwp_cost_search.py`: exact-oracle comparisons and certificate regressions.
- `configs/hwp-guided-search.yaml` and a small `scripts/run_hwp_guided_search.py` reusing study helpers.
- `docs/hwp-guided-search.md` and one compact results report.

Reuse existing circuit emission, normalization, synthesis, resource counting, and verification. Do not add another circuit schema, artifact-replay stack, optimizer registry, or dashboard. Leave historical experiments outside the default command. Refactor helpers only where concrete duplication appears.

Required tests:

1. Same cost optimum as the existing exact frontier on tiny cases and several rational weights/hard caps.
2. Every structural and transferred bound is <= an independently enumerated tiny optimum.
3. Bad/mismatched certificates are rejected; approximate incumbent values are never used as lower bounds.
4. Timeout during expansion keeps a valid gap; no-incumbent timeout is not INFEASIBLE.
5. All returned incumbents reconstruct into feasible circuits with matching modeled resources.
6. The unsupported witness remains selectable under the known hard limits, without being asserted to improve unrestricted linear cost.

Run existing relevant semantic/resource tests once. Do not create tests for report formatting or repeat massive verification after documentation-only changes.

## 11. Commit sequence and stopping decisions

1. **Pin and diagnose:** accessible source, verified model contract, frozen costs, current exact/reference cost table.
2. **Search and bounds:** one cost-directed solver, rational structural bounds, sound timeout handling, tiny exact-oracle tests.
3. **Reuse and compare:** archived feasible seeds/certificates, matched ablations, concise cost-gap report.

Stop after these three commits and assess:

- If bounds close the gap faster at matched total cost, retain the method and test larger supported cases.
- If only good seeds help, report that result; do not credit geometric reasoning that did not help.
- If bounds are too weak or their computation costs more than they save, identify the actual bottleneck before adding stronger machinery.
- If the existing full-frontier DP wins across many queries, keep it for that use case.
- If no current construction improves the selected linear costs, keep search-efficiency and synthesis-quality claims separate.
- If generating options dominates cost, consider the gated pricing experiment.

The reviewable final output is an emitted circuit, its measured resources, its model-relative [L,U] interval, and a small comparison explaining where runtime was saved. A new report label or a new Pareto point alone does not satisfy the milestone.

## 12. Prior work informing this test

- Bökler, Parragh, Sinnl and Tricoire, *An outer approximation algorithm for multi-objective mixed-integer linear and non-linear programming*: https://arxiv.org/abs/2103.16647 . Establishes the use of scalar optimization oracles and bounding facets; it does not make a difficult synthesis oracle inexpensive.
- Dunbar, Sinha and Schaefer, *Relaxations and Duality for Multiobjective Integer Programming*: https://arxiv.org/abs/2309.08801 . Relevant to supported/unsupported points and the scope of relaxation bounds.
- *Mathematical Optimization*, column generation for cutting stock: https://scipbook.readthedocs.io/en/latest/bpp.html#column-generation-method-for-the-cutting-stock-problem . Shows restricted patterns, dual-guided generation, and the distinction between LP completion and integer optimality.
- Existing HWP study/model snapshots at remote commit `8534292` document the finite library, current witness, baseline correction, and outstanding source availability. Their reported solver guarantees remain subject to source review and reproduction.

Novelty is not claimed for branch-and-bound, Pareto pruning, supporting half-spaces, or column generation. A potential contribution would be a demonstrably effective HWP-specific construction generator or bound, supported by fair circuit and runtime evidence.
