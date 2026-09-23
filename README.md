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

The workflow normalizes a `PhaseProgram`, emits shared construction seeds, and
applies exact rewrites through PyZX, optional Feynman, or a limited clean-scratch
phase-polynomial action. Every accepted circuit is checked against its verified
parent chain, scheduled, and counted as `(T, T_depth, allocated ancillas)`
before one immutable final objective and hard limits choose the endpoint.

The bounded controller supports adaptive or frozen initial preference vectors,
fixed static preferences, and two successive fixed pass orders, all using the same seeds
and action library. Its attempt trace records intermediate resource changes,
including rejected rewrites. `--force` rebuilds only JSON checkpoints below
the configured `results/` subdirectory. Each reported Pareto alternative has
an emitted circuit and replayable proof chain in the policy's circuit artifact.

The default comparison contains `independent`, `shared_parity`, and
`hwp_adder_unitary`. The HWP construction emits the staged adder/compressor
network described by Kivlichan et al. and reverses it for unitary cleanup.
Distinct positive singleton predicates use an audited in-place input layout;
general predicates keep the copied-parity layout. Toffolis use the exact
seven-T, three-T-layer Amy-Maslov-Mosca decomposition. This adaptation remains
more expensive than the HWP paper's measurement-assisted cleanup and is
labeled accordingly.

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

The new iterative comparison is separate from the historical one-shot report:

```bash
python -m collective_phase audit --config configs/adaptive-comparison.yaml
python -m collective_phase run --config configs/adaptive-comparison.yaml
python -m collective_phase verify --results results/raw/iterative-ancilla
python -m collective_phase report --results results/raw/iterative-ancilla \
  --output reports/iterative-ancilla.md
```

Its fixed weighted objective uses positive configured reference scales and the
same hard limits for every policy. Synthetic inputs are explanatory development
diagnostics, not held-out evidence. Exact phase-block scratch resynthesis is
documented in [docs/backend-applicability.md](docs/backend-applicability.md).
The measured run uses the pinned optional Feynman release available on `PATH`;
the release archive digest and the unsupported-backend behavior are documented
there. Smaller count-first and depth-first diagnostics use
`configs/ancilla-count.yaml` and `configs/ancilla-depth.yaml`; each can be run,
verified, and reported with the same CLI commands and its configured results
directory.

Start review with [docs/review-guide.md](docs/review-guide.md). The precise
semantic and accounting contracts are in [docs/semantics.md](docs/semantics.md)
and [docs/resource-model.md](docs/resource-model.md). Source mapping and known
limits are in [docs/hwp-implementation-audit.md](docs/hwp-implementation-audit.md)
and [docs/prior-work-matrix.md](docs/prior-work-matrix.md).

## Interpretation Limits

The current evidence shows an enabling construction/backend sequence, but a
fixed pass order reaches the same development endpoint. The balanced study
ties the frozen initial preference vector on all five cases, so it does not establish that
recomputation improves search. The exact depth diagnostic uses extra clean
ancillas to reduce T-depth, but the count diagnostic finds no T-count decrease.
The study is unitary-only;
measurement-assisted and catalytic performance comparisons remain unsupported.

Historical reports are indexed in [reports/README.md](reports/README.md); their
recorded numbers are preserved rather than retroactively revised.

## Private Research Record

Project-local ARA records claims, evidence, and research milestones in the
ignored `ara/` directory. See [docs/ara.md](docs/ara.md) for the pinned setup,
scope, and private publication policy.

## Resource-Constrained HWP Synthesis

The finite-library Pareto study is independent of historical pass-order search.
It composes verified HWP/direct blocks in complete waves and answers minimum-T
queries under depth and clean-workspace caps. Read
[the model and construction audit](docs/hwp-pareto-model.md) and
[the recorded study](reports/hwp-pareto-study.md).

```bash
python -m pip install -e '.[test,study]'
python scripts/run_hwp_pareto.py --plot
python scripts/run_hwp_pareto.py --verify
```

The exact guarantee applies to the declared finite library and wave model.
Actual emitted circuits and optional optimized children are verified separately.

The [interleaved-search milestone](docs/hwp-interleaved-plan.md) keeps the same
construction family, preserves local tradeoffs, and lets partial waves yield to
shared rotation refinement. Optional certified load bounds coordinate workspace,
data-wire conflicts, and original block boundaries. For example:

```python
from collective_phase.hwp_symbolic import SymbolicLibrary
from collective_phase.hwp_cost_search import symbolic_search
from collective_phase.lowering import RotationSynthesizer

library = SymbolicLibrary(program, 1e-4, RotationSynthesizer(seed=0),
                          max_batch=8, orderings=('staged', 'readiness'))
result = symbolic_search(library, (1, 0, 0), ancilla_max=4, depth_max=120,
                         interleave=True, coupled_bounds=False,
                         target_cost=204, timeout_seconds=3)
# A returned plan is verified. Inspect status and L/U on timeout;
# reaching the requested target alone does not establish optimality.
```

Run `python scripts/run_hwp_interleaved_study.py` for the frozen development
comparison against upfront refinement and strong batching. The first query's
budget includes library setup; warm queries reuse that trial's caches. See
[the resulting comparison](reports/hwp-interleaved-study.md) for outcomes and limits.

The [constrained nine-rotation experiment](docs/hwp-nine-experiment.md) adds
opt-in Pareto-aware endpoint search (`pareto_ties=True`), a block-size partition
lower bound (`partition_bounds=True`), and progress ordering (`progress_order=True`).
Scalar `OPTIMAL` and `stats['endpoint_certified']` are separate guarantees.
Run `python scripts/run_hwp_nine_study.py` to compare these ablations with an
independent native partition/scheduling baseline and coupled two-group probes.
