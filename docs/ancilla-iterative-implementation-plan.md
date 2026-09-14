# Iterative optimization with ancilla-sensitive transformations

Date: 2026-09-14

Repository: `gcc-bug/t-tradeoff`

Implementation branch: `research/adaptive-tradeoff`

Inspected remote base: `9999766079edb649ae5722bf995e7fec9e5bb90b`

This handoff updates the next milestone in `docs/adaptive-tradeoff-plan.md`. Continue on the existing branch; do not reset it to the inspected commit. Read applicable `AGENTS.md` files and inspect local changes first. Local changes discussed with Codex may not yet have been pushed. Preserve completed repairs and unrelated work. This commit contains a plan only; it does not implement or validate the proposed optimizer.

## 1. Next goal and scope

Produce a small, inspectable experiment that answers:

> Can decisions based on the current circuit combine established ancilla-sensitive transformations more effectively than static decisions, under the same compilation budget?

The immediate deliverable is a verified multistep search with an actual ancilla-changing action, a fair static comparison, and an honest positive or negative result. Ancillas remain a first-class objective and constraint alongside T-count and T-depth. Workspace release followed by reuse is an optional mechanism to investigate, not a required story to manufacture.

Keep the existing phase-block input family and unitary Clifford+T model. Reuse PyZX, Feynman, and audited HWP. Begin with exact post-synthesis transformations and certified region boundaries. Do not add measurement-assisted cleanup, catalytic preparation, arbitrary intermediate cleanliness inference, a general pebbling engine, hardware runtime models, or new approximate synthesis backends for this milestone.

Engineering success requires working iteration, verified resource alternatives, and reproducible comparisons. Research success additionally requires a repeatable advantage or a concrete explanation of why a useful continuation is found more efficiently. No percentage improvement or adaptive win is promised.

## 2. Findings confirmed in the inspected base

| File or interface | Current behavior | Required change |
| --- | --- | --- |
| `src/collective_phase/search.py:run_policy` | Proposals generated once; backend outputs are never expanded | One iterative engine with parent-linked states |
| `_proposal_order` | Policies without the lookahead label can optimize only the independent seed | Identical seed/action access for every policy |
| `fixed_order` | Orders independent attempts rather than successive passes | Apply each pass to the previous verified output |
| `_adaptive_priority` | Reads logical Toffolis from original construction metadata | Use current emitted structure and supported action applicability |
| `verification/lowered.py:verify_optimized_lowered_circuit` | Revalidates the source through construction-only verification; assumes unchanged candidate and original width | Validate a bound verified parent and the actual replacement contract |
| `resources.py:estimate_resources` | `allocated_qubits` cannot exceed original data plus construction workspace | Separate current layout from construction provenance |
| `adapters/feynman.py` | `.i` and `.o` include all declared wires; parser rejects new wires; width derives from the original candidate | Add an explicit, audited clean-ancilla interface and current wire map |
| `adapters/_pyzx_circuit.py` | Checks equal-width whole-unitary equivalence | Keep this valid path; use a separate clean-input contract when needed |
| `baselines/hwp.py` | Batches compute, phase, uncompute, then reuse workspace | Do not claim a release bottleneck without evidence |
| `tests/test_search.py` | Main lookahead test changes both seed access and call budget | Replace adaptive-superiority assertion with independent mechanism and fairness checks |

The old reported path `(200,50,0) -> (190,73,7) -> (176,114,7)` demonstrates a useful construction-plus-optimization combination. Fixed order matches its endpoint. It is a development regression case, not evidence of adaptive superiority.

## 3. Keep the resource and semantic contracts small

### 3.1 Current allocation

For this milestone, `A` means additional logical wires allocated to the current emitted implementation after justified wire remapping. It is not the count of temporarily occupied wires. Keep the existing serialized `peak_workspace` field if needed for compatibility, but explicitly label its meaning in reports; avoid a broad schema migration.

Track separately:

- `A_max`: user budget.
- Current logical data/interface wires and explicit workspace wire map.
- Workspace known clean at each supported replacement boundary.

Construction metadata remains provenance. It is not the maximum allowed size of future circuits. Update all width consumers together: event validation, resource counting, adapters, dense checking, hashing, and serialization. Preserve data-wire identity. Removing or compacting workspace requires a valid boundary contract, not a gap in gate activity. Use explicit `None` handling for unspecified allocation.

Do not build time-indexed workspace occupancy yet. If later evidence requires overlapping regions, introduce lifetimes only for certified regions and measure their shared schedule. Never derive availability from an idle wire.

### 3.2 Replacement contracts

Support two explicit kinds of exact rewrite:

1. **Whole-unitary rewrite:** same live interface, exact equivalence up to a tracked global phase. Existing workspace must be treated as arbitrary input unless its cleanliness is certified at this boundary.
2. **Clean-extension rewrite:** a replacement may introduce `k` fresh zero-initialized scratch wires and must satisfy, for every live input `psi`,

   `V_new (|psi> |0^k>) = exp(i phi) (V_old |psi>) |0^k>`.

The identity must hold for arbitrary, possibly entangled live inputs. Returning fresh scratch to zero is part of the obligation. For implementations with different pre-existing clean-workspace counts, compare their common logical isometry with consistent wire embeddings and require all scratch outputs clean.

Initially use a contiguous supported region of the current gate stream, or the whole circuit. Fresh scratch belongs to that action and is restored at its exit. Recompute region locations after every rewrite; old event offsets or semantic annotations cannot survive arbitrary global optimization automatically. This provides real ancilla-changing actions without general intermediate-state analysis.

### 3.3 Verification through iteration

Keep construction verification as the root of a chain. Each child binds to its actual verified parent's events, wire contract, global phase, and error contract. A status string or matching hash alone is not an equivalence proof.

- Validate the root once per run, caching only by the complete immutable input contract.
- Verify each exact edge against its parent with the appropriate contract.
- Preserve the parent's approximation bound across exact rewrites; do not charge the original rotation error again.
- Accumulate and verify global-phase corrections at every edge, including serialization/replay.
- Independently check a small final circuit against the original target using the existing dense isometry machinery.
- When dense checking is too large, accept only a supported compositional proof. Otherwise return inconclusive, never an inherited success label.

Do not infer equivalence between independently approximated direct and HWP circuits: both can satisfy the same target tolerance while differing from each other. Keep them as independently verified seeds. Any later symbolic reconstruction must be revalidated against its logical target and complete error budget, not described as an exact backend edge.

Feynman's upstream `feynver` documentation permits different ancillas with matching primary inputs. Probe the pinned executable and its output-cleanliness/global-phase semantics before adding a new verifier. Reuse this path only if it establishes the required contract; do not assume current `.qc` declarations already express it.

## 4. First establish a usable ancilla-sensitive action

The preferred action is ancilla-assisted T-depth resynthesis using Amy–Maslov–Mosca/T-par. It must accept a supported current region and a scratch allowance, and return actual gates, actual wire mapping, and a checkable equivalence result.

Perform a bounded capability probe before extending the controller:

1. Inspect the pinned Feynman release's help, parser, and relevant implementation. Record whether extra clean ancillas are exposed through CLI options, circuit declarations, or a library interface. Do not invent a flag or infer support from the paper alone.
2. Run the zero-scratch and positive-scratch variants on the same exact region. Record actual allocated scratch, emitted T-count, scheduled T-depth, cleanliness, and verification result. Appending unused wires is not a successful action.
3. Use the published ancilla-assisted Toffoli/CCZ construction as a diagnostic. Then test at least one multi-gate phase region from the existing workloads. Gadget success alone is insufficient for the workload claim.
4. Expose only allowances the backend actually respects. Filter by total current allocation plus required fresh scratch, and recount the emitted result.

If the pinned release cannot provide this action, first attempt a small adapter to an available upstream implementation. Record exact revision, license, build command, and supported input class. Do not let building unrelated relational passes become a prerequisite.

If no usable interface is available, permit one explicitly limited implementation of a published CNOT+phase ancilla-assisted construction, with a documented correspondence to the source method. Support a narrow exact gate set and reject unsupported regions. Do not build a general synthesis optimizer or a collection of isolated Toffoli rules. Report this fallback as a reproduction, not a competitive T-par implementation. Its limitations must appear in the comparison.

Also retain a zero-scratch option for each supported region. Initially, retain the pre-expansion parent as that option rather than trying to remove arbitrary entangled workspace from an optimized result. If resynthesis supports replacement at several scratch allowances, allow these replacements explicitly and verify their clean boundary. Do not count selecting a different initial seed as an in-search ancilla change.

**Gate A:** one nontrivial current-circuit transformation demonstrably changes `A`, respects its clean contract, and yields a meaningful count/depth alternative. A depth gain is required to establish a workspace-for-depth mechanism; it is not required for every allowance or every input. If no useful workload case exists, report that result before adding lifetime scheduling.

## 5. One iterative search engine

Refactor `run_policy`; do not add another independent runner. Reuse `SearchState`, `SearchResult`, `FinalObjective`, and `SelectionLimits` where possible.

A state needs current emitted circuit/layout, measured resources, verified provenance, immutable final objective, parent ID, transformation depth, and current action applicability. A proposal identifies the parent, current region, backend, scratch allowance, predicted priority, and reason.

Implement this loop:

```text
validate/deduplicate all common seeds
initialize bounded exploration pool and best feasible result
while an untried expansion fits the remaining budgets:
    discover supported regions/actions on retained current states
    compute priorities using the chosen policy
    select an untried (state, region, action, allowance)
    execute with remaining-time timeout
    verify against that parent; recount the whole result
    record the attempt immediately, including failure or no change
    update best feasible result and bounded exploration pool
    regenerate priorities/applicability for affected states
return best feasible result, final Pareto alternatives, and attempt trace
```

Default pilot bounds: at most three transformations after a seed, four retained states, twelve attempted transformations, and a 60-second search deadline. These are initial engineering settings, not tuned performance claims. Put them in configuration and freeze them before comparing policies. Report root preparation separately and include it in total user compilation time.

Retain the best feasible state plus a few structurally distinct alternatives using one deterministic rule shared by all policies. Permit temporarily worse final-objective values within all hard limits. Do not prune solely by `(T,D,A)`: structurally different circuits can have different continuations. Use normalized gate stream, wire contract, and relevant transformation context for identity; equivalent tuple values are not identity. Reject no-op repeats and bound cycles/depth. Keep the final Pareto display separate from the exploration pool.

For this milestone, all retained states obey the configured hard limits, including T/depth limits if present. No feasible seed means **no feasible seed found under this search policy**, not mathematical infeasibility. This intentionally leaves temporary hard-limit violations outside scope and must be stated when reporting results.

### Priority policy: implement one auditable heuristic

Keep the final objective and its normalization references fixed throughout a run. Local action priority can change. Use normalized current measurements and concrete applicability, not old logical-Toffoli counts or a generic positive ancilla orientation for every backend.

A minimal design is: fixed final weights plus current proximity to resource bounds, combined with current critical-path evidence and supported action effects. For positive bounds, define pressure explicitly, for example `max(0, resource/bound - 0.8)`; a zero ancilla bound disables allocating actions directly. Omitted bounds contribute no pressure. Declare coefficient values in the configuration and hold them fixed across evaluation cases. The pressure must describe the proposal's current state, not only the global incumbent.

For each attempt, record the full current `(T,D,A)` priority vector and the evidence that influenced its rank. Explain a change in action choice, not just a changed number. Unknown benefit is allowed; do not pretend a depth-oriented action necessarily reduces depth. Use one small, common exploration rule so an initially unattractive action can be tried. Frozen-priority ablation must retain identical applicability discovery, pool management, and exploration behavior.

**Gate B:** a real backend output is the input to a second transformation, both edges verify, the current-circuit priorities are recomputed, and final resources come from the actual final event stream.

## 6. Fair comparison and evidence

Replace the current policy proliferation with these comparisons:

| Policy | What changes relative to the common engine |
| --- | --- |
| Adaptive | Recompute the declared local priority rule from current states |
| Frozen priorities | Freeze the priority weights/evidence at the corresponding seed; keep current applicability and all other search behavior |
| Static preferences | Predeclared count-first, depth-first, ancilla-first, and balanced priorities |
| Fixed successive sequences | Apply fixed backend/action sequences successively to verified outputs |

All policies receive the same seeds, supported regions, scratch allowances, action library, sequence-depth bound, pool capacity, and hard limits. Give them the same opportunity set; they may visit different states. Include at least both orders of the working count-oriented and depth/ancilla-oriented actions. Unsupported steps are recorded and handled consistently.

Compare against the combined best alternatives from static runs, while charging their combined compilation budget. Do not compare twelve adaptive calls with four separate twelve-call static runs as if their cost were equal. Report both a matched-total-budget comparison and, if useful, the more expensive static envelope with its true cost.

Measure backend execution, verification, counting/scheduling, controller time, and total wall time without double counting. Adapter time currently includes verification work; separate its timing where practicable. Timeouts and unsuccessful attempts count. Enforce remaining deadlines inside subprocess calls rather than checking only after they return. Use identical cache policy and initial cache contents per policy; do not warm later policies with earlier results silently. Count cached proposals and cache hits explicitly.

Use a small frozen study:

- An exact ancilla-assisted diagnostic from prior work.
- The existing four-predicate witness and overlapping-dependency case, labeled development inputs.
- One existing application-derived graph phase block.
- One preselected negative control with little relevant parallelism or no applicable ancilla action.

Use at least zero workspace and two positive allowances that span an observed action threshold, chosen in the capability probe rather than tuned to adaptive wins. Exercise count-first with a depth cap, depth-first with a count cap, and one fixed balanced objective. Ancilla-first is meaningful with nontrivial T/depth requirements; include a zero-ancilla feasible case as a control, not as an optimization achievement.

Retain theta `0.173` and total error `1e-4` for applicable existing approximate workloads. Exact diagnostics need no artificial approximation. Fix angle/error allocation consistently across policies. These are development experiments; broader or held-out benchmarks follow only after a mechanism is established.

The trace records each decision when it happens: parent/output IDs, region, allowance, applicability or rejection reason, priority vector, before/after resources and fixed objective, verification outcome, and elapsed work. The winning parent chain is a derived view. Include enough top-ranked alternatives to explain a decisive choice without dumping every candidate circuit into Markdown.

**Gate C:** one concise report distinguishes (i) ancilla-action capability, (ii) multistep interaction, and (iii) adaptive advantage. Passing (i) and (ii) does not imply (iii). Report ties and regressions. A workspace-release claim additionally needs a real earlier obstruction and a later action that uses the changed availability; do not infer it from lower allocation alone.

## 7. Files, commits, and essential tests

Keep changes in the existing modules. Add at most one small workspace-action module if an upstream wrapper needs it; avoid a general registry/framework. A small contract dataclass may live alongside `LoweredCircuit`.

| Commit | Main files | Reviewable outcome |
| --- | --- | --- |
| 1. Ancilla capability probe | `adapters/feynman.py`, `docs/backend-applicability.md`, focused fixture | Actual supported interface, emitted workspace alternative, and known limitations |
| 2. Current layout and verified edges | `lowering/lower.py`, `resources.py`, `verification/lowered.py`, adapters | Exact chained rewrites and clean-ancilla dimension changes work without forging construction metadata |
| 3. Iterative shared search | `search.py`, `selection.py` only as needed | Parent expansion, current priorities, bounded retention, honest feasibility and trace |
| 4. Fair experiment and cleanup | `configs/adaptive-comparison.yaml`, manifest, `experiments.py`, `reporting.py`, tests | Same opportunities/budgets; genuine fixed sequences; obsolete lookahead branches removed |
| 5. Measured result and review guide | `reports/adaptive-comparison.md`, `docs/evaluation-contract.md`, `docs/resource-model.md`, `docs/review-guide.md`, README | Small result table, causal trace, limitations, explicit next research decision |

The probe may use scratch scripts before production contract support exists; commit a diagnostic fixture and findings rather than an unsafe selectable action. Each implementation commit should remain coherent. If the local checkout already implements a step, verify it and record its commit instead of duplicating it.

Retain only tests that protect substantive behavior:

1. Two exact real rewrites compose; the second accepts a verified optimized parent. Tampering with the parent or final gates invalidates the chain, including when dense checking is skipped.
2. A clean-ancilla replacement may differ on nonzero scratch inputs but must preserve every live input and return scratch clean. Include a deliberately uncleared or entangled scratch output that fails.
3. Added scratch and remapped wires are counted correctly; budget zero and an exact budget boundary behave correctly; data-wire identities are preserved.
4. The same valid seeds/actions are accessible to every policy; fixed sequences consume prior outputs. A small controlled fixture can test controller behavior, but cannot support a quantum-performance claim.
5. A temporarily objective-worse valid state can survive bounded retention and enable a later step; a no-op cycle terminates. Do not require every run to exhibit this behavior.
6. Final target/global-phase/error contract remains valid after the selected chain; hard-limit rejection and failed verification never produce a selectable state.

Keep existing arithmetic truth tables, event-binding mutation regressions, and one small end-to-end quantum check. Replace the confounded lookahead test; do not preserve its expected adaptive win. Remove dead lookahead aliases, duplicated selection/report paths, stale orientation claims, and tests tied only to those removed behaviors. Keep historical results explicitly labeled rather than spending this milestone rewriting old reports. Avoid snapshot tests for full Markdown, duplicated adapter proof checks, and a new generic audit subsystem.

Once focused regressions and the affected integration suite pass, run the small frozen experiment. Do not broaden optional testing to postpone the research result. Record unavailable backends and verification-inconclusive cases transparently.

## 8. Commands and acceptance checklist

Use the existing CLI and preserve its shape. After implementation, the expected workflow is:

```bash
python -m pytest tests/test_search.py tests/test_adapters.py tests/test_lowered_verification.py tests/test_lowering_resources.py
python -m collective_phase audit --config configs/adaptive-comparison.yaml
python -m collective_phase run --config configs/adaptive-comparison.yaml
python -m collective_phase report --results results/raw/adaptive-comparison
```

Do not claim these commands were executed by the author of this plan. Adjust only for actual local dependency/setup requirements and documented configuration changes. Store final artifacts through the repository's existing workflow.

The implementation handoff is complete when:

- A real ancilla-sensitive action works on a current circuit, with measured emitted costs and a verified clean contract.
- Two or more transformations compose; priorities and applicability use the transformed state.
- All policy comparisons share seeds, actions, allowable depths, retention rules, limits, and consistent total-cost accounting.
- A short attempt trace explains successes, failed attempts, and the selected circuit.
- The report explicitly states whether adaptation beats, ties, or loses to the strongest matched static comparison.
- The active code remains reviewable through construction/action, verification/resource, search, and experiment paths; old one-shot machinery is removed.

If the action works but adaptation does not help, retain the useful integration and state the negative result. If the action is irrelevant to these workloads, examine the input structure and supported action space before expanding the controller. Neither outcome justifies manufacturing a workspace-release example or adding more policy names.

## Sources and inspected references

- [Inspected branch base](https://github.com/gcc-bug/t-tradeoff/tree/9999766079edb649ae5722bf995e7fec9e5bb90b): file-level findings above were checked through repository reads; quantum benchmarks were not rerun for this plan.
- [Amy–Maslov–Mosca, T-depth optimization](https://arxiv.org/abs/1303.2042): established ancilla-assisted resynthesis; use as an action source, not a novelty claim.
- [Selinger, T-depth-one circuits](https://arxiv.org/abs/1210.0974): published ancilla-assisted diagnostic and its limitations.
- [Feynman upstream documentation](https://github.com/meamy/feynman): `feynver` accepts circuits with matching primary inputs and potentially different ancillas. Exact pinned-release behavior still requires the planned probe.

This plan takes precedence over older requirements that equate lookahead with seed access, require workspace release as the sole mechanism, or require adaptive wins as a test expectation.
