# Collective Phase Workbench

This repository compares established constructions for one canonical
parity-phase target:

```text
U(theta)|x> = exp(i theta sum_j p_j(x)) |x>,
p_j(x) = a_j . x XOR b_j.
```

Exact angle identities, term multiplicity, block boundaries, and little-endian
mask semantics are preserved by one shared normalization pass. The supported
target is a diagonal parity block; controlled application and general
commuting-Pauli diagonalization are outside the current contract.

## Workflow

The schema-v3 workflow normalizes a `PhaseProgram`, emits shared construction
seeds, and optionally applies exact whole-circuit optimization through PyZX or
Feynman. Every accepted circuit is checked against its source, scheduled, and
counted as `(T, T_depth, peak allocated workspace)` before one immutable final
objective and its hard limits choose the endpoint.

The controller supports fixed priorities, a fixed pass order, state-dependent
priorities, and bounded construction/backend lookahead. Search records every
backend call, elapsed backend time, rejection reason, accepted decision, and
Pareto point. `--force` rebuilds only JSON checkpoints below the configured
`results/` subdirectory so stale result schemas cannot contaminate a run.

The default comparison contains `independent`, `shared_parity`, and
`hwp_adder_unitary`. The HWP construction emits the staged adder/compressor
network described by Kivlichan et al. and reverses it for unitary cleanup. This
adaptation is more expensive than the paper's measurement-assisted cleanup and
is labeled accordingly.

The former ANF popcount, dependent-triple wrapper, legacy macro, and catalytic
estimate are retained only in Git history and historical reports. They are not
production methods or default competitors.

## Setup

Python 3.10 or newer is required:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest
```

`pygridsynth==2.0.0` supplies ancilla-free approximation of generic `Rz`
rotations. Exact multiples of `pi/4` bypass approximate synthesis. All methods
receive the same total operator-norm error budget, and each full-circuit
alternative is lowered with its actual rotation count. PyZX `0.9.0` supplies
the required exact post-synthesis optimization. Feynman is an optional external
executable; a missing executable is reported as unsupported rather than
replaced by a local stand-in.

## Default Study

```bash
python -m collective_phase audit --config configs/default-study.yaml
python -m collective_phase acquire --config configs/default-study.yaml
python -m collective_phase run --config configs/default-study.yaml
python -m collective_phase verify --results results/raw/default-study
python -m collective_phase report --results results/raw/default-study \
  --output reports/default-study.md
```

The fixed workload has four explanatory or negative-control cases and three
previously used checksum-pinned QED-C graphs. Those public graphs are development
data, not held-out evidence. The configuration declares a generic angle,
`1e-4` total error, eight workspace qubits, a T-count objective, and explicit
hard limits.

The adaptive development comparison is separate:

```bash
python -m collective_phase audit --config configs/adaptive-comparison.yaml
python -m collective_phase run --config configs/adaptive-comparison.yaml --force
python -m collective_phase verify --results results/raw/adaptive-comparison
python -m collective_phase report --results results/raw/adaptive-comparison \
  --output reports/adaptive-comparison.md
```

Its fixed weighted objective uses positive configured reference scales and the
same hard limits for every policy. The two synthetic inputs are explanatory
development diagnostics, not held-out evidence.

Start review with [docs/review-guide.md](docs/review-guide.md). The precise
semantic and accounting contracts are in [docs/semantics.md](docs/semantics.md)
and [docs/resource-model.md](docs/resource-model.md). Source mapping and known
limits are in [docs/hwp-implementation-audit.md](docs/hwp-implementation-audit.md)
and [docs/prior-work-matrix.md](docs/prior-work-matrix.md).

## Interpretation Limits

The current evidence shows an enabling construction/backend sequence, but a
fixed pass order reaches the same development endpoint. It therefore does not
establish that adaptive priority is superior. The study is unitary-only;
measurement-assisted and catalytic performance comparisons remain unsupported.

Historical reports are indexed in [reports/README.md](reports/README.md); their
recorded numbers are preserved rather than retroactively revised.
