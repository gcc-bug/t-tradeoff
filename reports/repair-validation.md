# Repair Validation

Date: 2026-09-08

Starting revision: `32ad1131eb16eabdeb04d75fd4b90f344ea0c7e9`.
The initial test suite passed 48 tests. The initial remediation suite passed 86
tests; the subsequent tradeoff-reporting extension passes 88 tests.

Environment:

- Python 3.13.7
- NumPy 2.4.4
- PyYAML 6.0.2
- pygridsynth 2.0.0

Validation performed:

```bash
python -m compileall -q src tests
pytest -q
python -m collective_phase audit --config configs/repair-pilot.yaml
python -m collective_phase acquire --config configs/repair-pilot.yaml
python -m collective_phase run --config configs/repair-pilot.yaml
python -m collective_phase verify --results results/raw/repair-pilot
python -m collective_phase report --results results/raw/repair-pilot \
  --output reports/m2-reliable-evaluation.md
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir TMPDIR
git diff --check
```

The PyPA `python -m build` frontend was not installed in the test environment;
the isolated wheel command above succeeded and produced
`collective_phase-0.1.0-py3-none-any.whl`.

The repaired pilot produced 104 successful rows. The tradeoff-focused replay
also produced 104 successful rows. All rows in each run were reconstructed
from schema-v2 artifacts and passed target, ideal semantics, deterministic
lowering, independent emitted-gate, synthesis-error, and resource replay.
Dense verification uses a declared memory preflight; larger gate streams are
labeled compositional rather than full numerical checks.

Mutation coverage rejects T to T-dagger changes, reversed CNOT direction,
missing cleanup, altered global phase, non-finite evidence, changed resource
counts, corrupted serialized gates, and macros relabeled as emitted.

Remaining limitations: the emitted HWP is an out-of-place ANF correctness
reference, not a competitive prior-construction reproduction. Catalytic and
measurement-assisted channels and joint synthesis are not primary evidence.
The canonical remote and Git history are identifying while publication mode is
undecided; any shared artifact still needs double-blind review.

The repository audit also reports no tracked license and requires human review
of contextual identity clues before release. The ARA lifecycle is not
initialized or wired; it was intentionally not installed as part of this
implementation repair.
