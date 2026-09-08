# Progress

Date: 2026-09-08

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

## Reproduction

```bash
python -m pip install -e '.[test]'
pytest
python -m collective_phase audit --config configs/tradeoff-pilot.yaml
python -m collective_phase acquire --config configs/tradeoff-pilot.yaml
python -m collective_phase run --config configs/tradeoff-pilot.yaml
python -m collective_phase verify --results results/raw/tradeoff-pilot
python -m collective_phase report --results results/raw/tradeoff-pilot \
  --output reports/m2-reliable-evaluation.md
```

Generated raw result rows remain ignored. The tracked configuration, manifest,
tests, reports, and implementation define the reproducible artifact.
