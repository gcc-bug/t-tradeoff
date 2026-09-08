# Progress

Date: 2026-09-07

## M0 - scope and audit

Implemented the semantic and resource decisions, dependency plan, and initial
prior-work matrix.  The source directory began with only the research plan and
is not a Git worktree.  The research-repository audit consequently cannot
inspect history/remotes; publication mode remains implicitly `undecided`.

Evidence: `python -m collective_phase audit --config configs/smoke.yaml`.

Unresolved: full claim-level literature audit for Kim, NCF, and graph
sparsification; Git history/remotes do not exist; no transitive lock file.

## M1 - inputs, IR, and B0

Implemented exact-angle IR, immutable checksum acquisition, deterministic
synthetic generators, the frozen QED-C subset, B0, candidate artifacts,
exhaustive semantics, coherent-state tests, and actual generic rotation
synthesis through pygridsynth.

The three frozen QED-C files were acquired successfully and matched their
declared SHA-256 digests.  Thirteen pilot cases produced a structural diagnosis.

Unresolved: acquire and classify a small HamLib spin subset; record finite input
coefficient precision for noninteger-weight future cases.

## M2 - baselines and diagnosis

B1 emits a deterministic shared anchor-row parity walk.  B2 and B3 implement
exact ideal semantics and published compositional non-Clifford formulas with
explicit parity, workspace, cleanup, catalyst preparation, error, and reuse
accounting.  Both remain `estimated_macro` because their arithmetic internals
are not emitted.  B4 is explicitly unavailable.

Unresolved: emit and independently verify HWP arithmetic/measurement branches;
reproduce a published numeric gadget table; integrate a compatible joint
synthesizer if an artifact is found.

## M3 - witness and hypothesis decision

The dependent-triple identity, detector, emitted unitary implementation,
failure regime, hypothesis card, and exact tests are implemented.  The bounded
generic run at `theta=0.173`, error `1e-4`, workspace 8 found emitted T-count
wins on all three frozen QED-C inputs and no T-count regressions over the full
13-case set.  This is a reason to continue the narrow mechanism, not a passed
research gate: emitted HWP, joint synthesis, the full angle/error grid, and the
precise prior-art overlap check are still required.  One public case regressed
in scheduled T-depth despite improving T-count.

## M4 - minimal detector/rewriter

A lexicographic disjoint-triple detector and transformation traces are present.
It deliberately performs no broad search or graph decomposition.

Unresolved: evaluate transfer on frozen public and held-out source categories.

## M5 - reproducible package

CLI, configs, manifests, checkpointed rows, circuit JSON, integrity verification,
and Markdown reporting are implemented.  Final evidence remains incomplete for
the reasons above.

## Reproduction commands

```bash
python -m pip install -e '.[test]'
pytest
python -m collective_phase audit --config configs/smoke.yaml
python -m collective_phase profile --config configs/smoke.yaml
python -m collective_phase run --config configs/smoke.yaml
python -m collective_phase verify --results results/raw/smoke
python -m collective_phase report --results results/raw/smoke --output reports/smoke-results.md
```

Next bounded action: emit and independently validate the ordinary-HWP adder
network, then rerun the same bounded configuration before expanding the grid.

`configs/pilot-initial.yaml` is the bounded first decision run: it uses every
case in the frozen pilot manifest but only angle `0.173`, total synthesis error
`1e-4`, eight workspace qubits, and the unitary profile.  It is not a replacement
for the full grid in `configs/pilot.yaml`.
