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

## Tradeoff evaluation

The current development pilot contains three checksum-pinned QED-C MaxCut
instances plus separately labeled diagnostics and negative controls. Its
primary output is the raw rotation-for-arithmetic tradeoff; T-count selection
is reported only as a secondary deployment policy:

```bash
python -m collective_phase audit --config configs/tradeoff-pilot.yaml
python -m collective_phase acquire --config configs/tradeoff-pilot.yaml
python -m collective_phase profile --config configs/tradeoff-pilot.yaml
python -m collective_phase run --config configs/tradeoff-pilot.yaml
python -m collective_phase verify --results results/raw/tradeoff-pilot
python -m collective_phase report --results results/raw/tradeoff-pilot \
  --output reports/m2-reliable-evaluation.md
```

Raw input downloads and generated result rows are ignored.  Their manifests,
checksums, configuration hashes, and exact acquisition URLs are tracked.

## Interpretation

The repaired runner uses explicit method identities. Emitted methods include
`independent`, `shared_parity`, `hwp_emitted`,
`hwp_emitted_triple_grouped`, `hwp_dependency_simplified`,
`dependent_triples_raw`, and `dependent_triples_selected`.
`hwp_macro_legacy` is shown only as historical formula evidence.

The evaluator first compares `dependent_triples_raw` with `independent` using
generic-rotation, logical-Toffoli, CNOT, and clean-workspace counts. It then
shows T-count and T-depth outcomes under the configured lowering. The current
triple rewrite is exactly reproduced by dependency-simplified HWP on every
pilot case, so the measured tradeoff is not reported as a surviving new method.
Joint synthesis, catalytic HWP, and measurement-assisted HWP remain unavailable
or unverified under matching semantics.

See [docs/semantics.md](docs/semantics.md),
[docs/resource-model.md](docs/resource-model.md), and
[docs/progress.md](docs/progress.md) before drawing research conclusions.
