# Progress

Date: 2026-09-09

## Refocused Construction Study

The default workflow now compares `independent`, `shared_parity`, and an
audited `hwp_adder_unitary` construction. The latter implements the staged
3-to-2 and 2-to-2 compressor network from Kivlichan et al.
arXiv:1902.10673v4 Appendix A.1. Its unitary adaptation explicitly pays
forward and reverse arithmetic rather than claiming measurement-assisted
cleanup costs. The old ANF implementation is capped at size eight and labeled
as a correctness reference.

The lowered verifier now binds ideal construction evidence, independently
checked rotation and Toffoli matrices, emitted event order, global phase, and
whole-circuit error allocation before issuing a compositional result. Forced
low-memory mutation tests cover T/T-dagger, CNOT direction, cleanup removal,
global phase, and metadata. Unsupported ideal evidence is ineligible.

Selection supports T-count, scheduled T-depth, and ancilla objectives with
explicit hard limits, deterministic tie-breaks, visible infeasibility, and
Pareto retention. Evidence strength is metadata rather than name membership.
The default report is method-neutral and separates arithmetic T from rotation T.

The fixed seven-case study produced 21 successful rows, all of which passed
artifact replay. Under its T-count policy, adder HWP is selected on every
unweighted case. On `independent_equal_angle`, it changes `(T, T-depth, A)`
from `(200, 50, 0)` to `(190, 73, 7)`, exposing a real objective tradeoff. The
weighted triangle-free case has no compatible multi-term group and falls back
to the direct circuit. Rotation synthesis remains the larger T component.

The fresh test run passes 121 tests with Python 3.13.7, NumPy 2.4.4, PyYAML
6.0.2, and pygridsynth 2.0.0. See `reports/default-study.md`.

This development study does not yet identify a recurring algorithmic gap. Its
weighted negative control confirms ordinary HWP's expected equal-angle
boundary, but one case is not a research claim. The next gated comparison is
an emitted, channel-verified measured or catalytic construction under matched
state-preparation and repeated-use accounting.

## Historical Milestones

## Starting evidence

Remediation began at revision
`32ad1131eb16eabdeb04d75fd4b90f344ea0c7e9`. The initial suite passed 48
tests with Python 3.13.7, NumPy 2.4.4, PyYAML 6.0.2, and pygridsynth 2.0.0.
The canonical Git remote and history are identifying. Publication mode remains
undecided, so double-blind safeguards are required for any shared artifact.

## M2-R - reliable evaluation

Implemented canonical block-local preprocessing, explicit method variants,
emitted unitary HWP arithmetic, full-circuit batch selection, raw and selected
triple methods, independent lowered-gate verification, schema-v2 artifact
replay, recomputed rotation/arithmetic tradeoff records, benchmark strata, and
matched reporting.

The repaired development pilot contains the original three checksum-pinned
QED-C inputs, eight diagnostics, and two negative controls at angle 0.173,
total operator-norm budget 1e-4, and workspace budget 8. All repaired rows and
artifacts pass replay. The current report treats raw rotation savings and added
arithmetic/workspace as the primary result; fully lowered T metrics and
objective-selected fallback are secondary. See
`reports/m2-reliable-evaluation.md`.

The tradeoff-focused pilot has 104 successful rows. The raw rule fires in 6 of
13 cases, matching 11 triples and exchanging 22 generic rotations for 22
logical Toffolis, 66 observed CNOTs, and three reusable clean ancillas. The
current test suite contains 88 passing tests.

M2-R status: complete for the unitary reference milestone. The emitted ANF HWP
is correctness-complete but is not a competitive reproduction of published
in-place or measurement-assisted HWP. Catalytic and joint-synthesis comparisons
remain unresolved and excluded from primary claims.

## M3-W - structural decision

The raw dependent-triple circuit and dependency-simplified HWP circuit have
the same emitted operation stream throughout the repaired pilot. The identity
is therefore subsumed by that HWP representation. It does not establish a new
method or a surviving witness.

M3-W status: not achieved. The current rule is retained as a regression and
teaching case. A broader mechanism should be explored only under a new bounded,
falsifiable hypothesis and a stronger baseline implementation.

## Current Reproduction

```bash
python -m pip install -e '.[test]'
pytest
python -m collective_phase audit --config configs/default-study.yaml
python -m collective_phase acquire --config configs/default-study.yaml
python -m collective_phase run --config configs/default-study.yaml
python -m collective_phase verify --results results/raw/default-study
python -m collective_phase report --results results/raw/default-study \
  --output reports/default-study.md
```

Generated raw result rows remain ignored. The tracked configuration, manifest,
tests, reports, and implementation define the reproducible artifact.
