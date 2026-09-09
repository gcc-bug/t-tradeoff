# Backend Applicability Probe

Audit date: 2026-09-09.

The initial integration accepts only exact post-synthesis rewrites of a fully
emitted unitary Clifford+T stream. Every workspace wire is declared as both an
input and an output at an external boundary. An output is eligible only after
source-to-result equivalence and global-phase correction; a backend timeout or
unknown result is not selectable.

| Backend | Revision | Interface exercised | Status |
| --- | --- | --- | --- |
| PyZX | `0.9.0` (`ac21c11...` tag) | Python `basic_optimization`, `full_optimize`, and graph `full_reduce` plus extraction | Working; exact count/depth alternatives reproduced on emitted HWP circuits |
| Feynman T-par | release `v0.1.0`, commit `2b52a0a...` | `.qc`, `-tpar -verify`; all wires in `.i` and `.o` | Working; a small HWP witness changed `(T,D,A)` from `(15,9,4)` to `(9,4,4)` |
| Amy-Lunderville relational passes | Feynman `d2c382a...` | Advertised `-apf`, `-qpf`, `-ppf` CLI | Source and BSD-2-Clause license located; build unresolved because Cabal/GHC are unavailable and the published binary predates these flags |
| NCF | arXiv:2510.13573v1 | Artifact search by paper title and method name | Unsupported; no public implementation/license was located, and general commuting Pauli groups are not automatically single-qubit groups |
| Trasyn | `ab5183c...`, MIT | `trasyn.synthesize` and Qiskit circuit entry point inspected | Out of initial scope: it performs approximate single-qubit synthesis and its error threshold is not a hard guarantee; integrating it after pygridsynth would require explicit error reallocation |

The working alternatives are sufficient to test exact count/depth scheduling.
They do not yet provide an optimizer-created workspace allocation alternative;
workspace variation currently comes from the audited HWP construction seeds.

On the synthetic development witness, PyZX optimization of the cap-4 HWP seed
changes `(190,73,7)` to `(176,114,7)`. Adaptive lookahead and the fixed-order
ablation both reach that endpoint, so this demonstrates an enabling
representation change but not an adaptive-priority advantage.
