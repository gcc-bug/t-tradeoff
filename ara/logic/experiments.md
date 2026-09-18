# Experiments

Retrospective verification plans for stored results; this compilation did not rerun them. Configuration files and evidence contain numerical settings.

## E01: Balanced policy ablation
- **Verifies**: [C01]
- **Setup**: Shared construction seeds, fixed weighted objective, matched hard limits, bounded calls, development inputs.
- **Procedure**: Compare adaptive, frozen, static-preference, and successive fixed-pass policies. Retain failures and charge portfolio compilation cost.
- **Expected outcome**: Preference recomputation would be supported only by an attributable verified endpoint benefit over frozen priorities.
- **Evidence**: `evidence/results/iterative-ancilla.md`
- **Run**: `configs/adaptive-comparison.yaml`, `src/collective_phase/experiments.py`; individual result pointers in `evidence/logs/log_pointers.md`.

## E02: Ancilla-for-depth diagnostic
- **Verifies**: [C01, C03]
- **Setup**: Exact phase target; compare clean-scratch allowance with a no-scratch control and prioritize depth.
- **Procedure**: Replay accepted phase rewrites, verify workspace cleanup, and schedule emitted primitives.
- **Expected outcome**: Extra clean workspace can permit concurrent phase operations, with fixed policies testing whether adaptation is essential.
- **Evidence**: `evidence/results/ancilla-depth.md`
- **Run**: `configs/ancilla-depth.yaml`, `src/collective_phase/experiments.py`; result pointers in the evidence log index.

## E03: Count-first negative control
- **Verifies**: [C01, C03]
- **Setup**: Same exact target family under a count-first objective and clean-workspace controls.
- **Procedure**: Compare policy endpoints and separate count changes from depth tie-breaks.
- **Expected outcome**: Depth-only gains should not be reported as count improvement or adaptive advantage.
- **Evidence**: `evidence/results/ancilla-count.md`
- **Run**: `configs/ancilla-count.yaml`, `src/collective_phase/experiments.py`; result pointers in the evidence log index.

## E04: Fixed sequence versus bounded discovery
- **Verifies**: [C02, C03]
- **Setup**: Checksum-pinned development graph; freeze the depth reference before discovery, hold error and workspace limits fixed.
- **Procedure**: Compare complete shared seed catalogs, fixed references, bounded discovery, and counterfactual sequences; replay the emitted winner.
- **Expected outcome**: A fixed sequence reaching the same endpoint removes the need to invoke adaptive preferences as its explanation.
- **Evidence**: `evidence/results/single-demonstration.md`
- **Run**: `scripts/inspect_tradeoff_sequences.py`, `configs/single-demonstration.yaml`, `results/single-demonstration/results.json`, `results/single-demonstration/winner.json`.

## E05: Finite-library HWP Pareto diagnostic
- **Provenance**: ai-executed
- **Verifies**: Staged O03; trace N08–N11.
- **Setup**: Frozen native, heterogeneous, overlapping-parity, QED-C and distinct-angle cases; normalized-term error budgets; deterministic unitary clean-scratch block boundaries.
- **Procedure**: Enumerate compatible subset constructions and legal waves, retain Pareto labels, compare strong uniform/per-group references, emit circuits and replay a common optimization opportunity.
- **Outcome**: One bounded mixed-layout gain remains after correcting the baseline; see the report for numbers. No repeatability or novelty conclusion.
- **Evidence**: `evidence/hwp-pareto/hwp-pareto-study.md`, `evidence/hwp-pareto/hwp-pareto-validation.md`.
- **Run**: `scripts/run_hwp_pareto.py` on `research/hwp-pareto-synthesis`; exact source hashes and worktree pointer in `evidence/hwp-pareto/source-manifest.json`.
