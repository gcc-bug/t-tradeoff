# Code and Configuration Index

Paths resolve to the canonical repository; no implementation is copied. Source modules are libraries, tests run with pytest, configs feed the documented CLI, and scripts retain their own entry points.

| File | Role |
|---|---|
| [configs/adaptive-comparison.yaml](../../configs/adaptive-comparison.yaml) | configs |
| [configs/ancilla-count.yaml](../../configs/ancilla-count.yaml) | configs |
| [configs/ancilla-depth.yaml](../../configs/ancilla-depth.yaml) | configs |
| [configs/default-study.yaml](../../configs/default-study.yaml) | configs |
| [configs/single-demonstration.yaml](../../configs/single-demonstration.yaml) | configs |
| [configs/smoke.yaml](../../configs/smoke.yaml) | configs |
| [data/manifests/adaptive-development.yaml](../../data/manifests/adaptive-development.yaml) | data |
| [data/manifests/ancilla-diagnostic.yaml](../../data/manifests/ancilla-diagnostic.yaml) | data |
| [data/manifests/pilot.yaml](../../data/manifests/pilot.yaml) | data |
| [data/manifests/refocus-study.yaml](../../data/manifests/refocus-study.yaml) | data |
| [data/manifests/smoke.yaml](../../data/manifests/smoke.yaml) | data |
| [pyproject.toml](../../pyproject.toml) | pyproject.toml |
| [scripts/inspect_tradeoff_sequences.py](../../scripts/inspect_tradeoff_sequences.py) | scripts |
| [src/collective_phase/__init__.py](../../src/collective_phase/__init__.py) | src |
| [src/collective_phase/__main__.py](../../src/collective_phase/__main__.py) | src |
| [src/collective_phase/adapters/__init__.py](../../src/collective_phase/adapters/__init__.py) | src |
| [src/collective_phase/adapters/_pyzx_circuit.py](../../src/collective_phase/adapters/_pyzx_circuit.py) | src |
| [src/collective_phase/adapters/common.py](../../src/collective_phase/adapters/common.py) | src |
| [src/collective_phase/adapters/feynman.py](../../src/collective_phase/adapters/feynman.py) | src |
| [src/collective_phase/adapters/phase_ancilla.py](../../src/collective_phase/adapters/phase_ancilla.py) | src |
| [src/collective_phase/adapters/pyzx.py](../../src/collective_phase/adapters/pyzx.py) | src |
| [src/collective_phase/baselines/__init__.py](../../src/collective_phase/baselines/__init__.py) | src |
| [src/collective_phase/baselines/arithmetic.py](../../src/collective_phase/baselines/arithmetic.py) | src |
| [src/collective_phase/baselines/common.py](../../src/collective_phase/baselines/common.py) | src |
| [src/collective_phase/baselines/hwp.py](../../src/collective_phase/baselines/hwp.py) | src |
| [src/collective_phase/baselines/independent.py](../../src/collective_phase/baselines/independent.py) | src |
| [src/collective_phase/baselines/shared_parity.py](../../src/collective_phase/baselines/shared_parity.py) | src |
| [src/collective_phase/circuit.py](../../src/collective_phase/circuit.py) | src |
| [src/collective_phase/cli.py](../../src/collective_phase/cli.py) | src |
| [src/collective_phase/experiments.py](../../src/collective_phase/experiments.py) | src |
| [src/collective_phase/inputs/__init__.py](../../src/collective_phase/inputs/__init__.py) | src |
| [src/collective_phase/inputs/manifest.py](../../src/collective_phase/inputs/manifest.py) | src |
| [src/collective_phase/ir.py](../../src/collective_phase/ir.py) | src |
| [src/collective_phase/lowering/__init__.py](../../src/collective_phase/lowering/__init__.py) | src |
| [src/collective_phase/lowering/lower.py](../../src/collective_phase/lowering/lower.py) | src |
| [src/collective_phase/lowering/primitives.py](../../src/collective_phase/lowering/primitives.py) | src |
| [src/collective_phase/lowering/synthesis.py](../../src/collective_phase/lowering/synthesis.py) | src |
| [src/collective_phase/preprocessing.py](../../src/collective_phase/preprocessing.py) | src |
| [src/collective_phase/profiles.py](../../src/collective_phase/profiles.py) | src |
| [src/collective_phase/reporting.py](../../src/collective_phase/reporting.py) | src |
| [src/collective_phase/resources.py](../../src/collective_phase/resources.py) | src |
| [src/collective_phase/search.py](../../src/collective_phase/search.py) | src |
| [src/collective_phase/selection.py](../../src/collective_phase/selection.py) | src |
| [src/collective_phase/verification/__init__.py](../../src/collective_phase/verification/__init__.py) | src |
| [src/collective_phase/verification/core.py](../../src/collective_phase/verification/core.py) | src |
| [src/collective_phase/verification/lowered.py](../../src/collective_phase/verification/lowered.py) | src |
| [tests/test_adapters.py](../../tests/test_adapters.py) | tests |
| [tests/test_compilers.py](../../tests/test_compilers.py) | tests |
| [tests/test_experiments.py](../../tests/test_experiments.py) | tests |
| [tests/test_hwp_arithmetic.py](../../tests/test_hwp_arithmetic.py) | tests |
| [tests/test_inputs_profiles.py](../../tests/test_inputs_profiles.py) | tests |
| [tests/test_ir.py](../../tests/test_ir.py) | tests |
| [tests/test_lowered_verification.py](../../tests/test_lowered_verification.py) | tests |
| [tests/test_lowering_resources.py](../../tests/test_lowering_resources.py) | tests |
| [tests/test_preprocessing.py](../../tests/test_preprocessing.py) | tests |
| [tests/test_search.py](../../tests/test_search.py) | tests |
| [tests/test_selection.py](../../tests/test_selection.py) | tests |
| [scripts/setup-ara.sh](../../scripts/setup-ara.sh) | private tooling installer; no research claim |

## Isolated HWP implementation

The HWP work is on `research/hwp-pareto-synthesis` in sibling worktree
`t-tradeoff-hwp-pareto`. Its module, study runner, tests and precision-contract changes
are identified by [the milestone source manifest](../evidence/hwp-pareto/source-manifest.json).
These files need not exist on the original working branch. Reproduction instructions
and exact source hashes are preserved with [the study](../evidence/hwp-pareto/hwp-pareto-study.md).
