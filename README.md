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

The reviewable workflow has three layers:

1. **Construct:** normalize a `PhaseProgram`, then emit named alternatives.
2. **Check and count:** verify ideal semantics and emitted decompositions, lower
   rotations with the pinned backend, schedule the event stream, and count
   `(T, T_depth, peak ancillas)`.
3. **Compare:** retain the Pareto set and select a verified alternative using
   an explicit objective and hard limits.

The default comparison contains `independent`, `shared_parity`, and
`hwp_adder_unitary`. The HWP construction emits the staged adder/compressor
network described by Kivlichan et al. and reverses it for unitary cleanup. This
adaptation is more expensive than the paper's measurement-assisted cleanup and
is labeled accordingly.

The ANF popcount, dependent-triple rewrite, legacy macro, and catalytic estimate
remain available only as correctness, diagnostic, historical, or unverified
methods. They do not enter the default ranking.

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
alternative is lowered with its actual rotation count.

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

Start review with [docs/review-guide.md](docs/review-guide.md). The precise
semantic and accounting contracts are in [docs/semantics.md](docs/semantics.md)
and [docs/resource-model.md](docs/resource-model.md). Source mapping and known
limits are in [docs/hwp-implementation-audit.md](docs/hwp-implementation-audit.md)
and [docs/prior-work-matrix.md](docs/prior-work-matrix.md).

## Interpretation Limits

Selecting the least costly existing circuit is infrastructure, not a novelty
claim. The current study is unitary-only. Measurement-assisted and catalytic
performance comparisons remain unsupported until their operations are emitted,
verified as channels under their actual resource-state assumptions, and charged
over matching repeated-use workloads.

Historical reports are indexed in [reports/README.md](reports/README.md); their
recorded numbers are preserved rather than retroactively revised.
