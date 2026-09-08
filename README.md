# Collective Phase

This repository is a research prototype for compiling equal-angle commuting
parity phases into Clifford+T resource models.  Its semantic target is

```text
U(theta)|x> = exp(i theta sum_j p_j(x)) |x>,
p_j(x) = a_j . x XOR b_j.
```

The prototype preserves exact angle-class identities and term multiplicity.
It currently supports diagonal parity blocks only; controlled application and
general commuting-Pauli diagonalization are deliberately unsupported.

For a short explanation of the current rotation-for-arithmetic tradeoff,
benchmarks, and evaluation flow, see
[docs/methodology-overview.md](docs/methodology-overview.md).

## Setup

Python 3.10 or newer is required.  A clean environment is recommended:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
```

`pygridsynth==2.0.0` supplies Ross-Selinger-style ancilla-free synthesis of
generic `Rz` rotations.  Exact multiples of `pi/4` bypass approximate
synthesis.  The compiler records the global phase introduced by translating
`P(theta) = diag(1, exp(i theta))` to `Rz(theta)`.

## Reproduction

The smoke suite is fully synthetic and requires no downloads:

```bash
python -m collective_phase audit --config configs/smoke.yaml
python -m collective_phase profile --config configs/smoke.yaml
python -m collective_phase run --config configs/smoke.yaml
python -m collective_phase verify --results results/raw/smoke
python -m collective_phase report --results results/raw/smoke
```

The frozen pilot currently contains three QED-C MaxCut instances selected by
fixed filename order, plus diagnostic and negative-control cases:

```bash
python -m collective_phase acquire --config configs/pilot.yaml
python -m collective_phase profile --config configs/pilot.yaml
python -m collective_phase run --config configs/pilot.yaml
python -m collective_phase verify --results results/raw/pilot
python -m collective_phase report --results results/raw/pilot
```

Raw input downloads and generated result rows are ignored.  Their manifests,
checksums, configuration hashes, and exact acquisition URLs are tracked.

## Interpretation

`independent`, `shared_parity`, and unitary `dependent_triples` results use
emitted Clifford+T operations.  `hwp` and `catalyzed_hwp` currently use
validated semantic macros with published compositional gate formulas, and are
marked `estimated_macro`.  `joint_synthesis` is reported as unavailable; no
NCF reproduction is claimed.

See [docs/semantics.md](docs/semantics.md),
[docs/resource-model.md](docs/resource-model.md), and
[docs/progress.md](docs/progress.md) before drawing research conclusions.
