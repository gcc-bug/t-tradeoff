# Backend Applicability Probe

Audit date: 2026-09-14 (ancilla probe); original backend audit 2026-09-09.

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
| Clean-scratch phase polynomial | local `amm-phase-polynomial-limited-v1` | Maximal contiguous CNOT/diagonal Clifford+T region; scratch allowances 1, 2, 4 | Narrow reproduction of phase-polynomial resynthesis, not Feynman T-par: emits parity compute, parallel phase layer, uncompute, original linear map. Canonical GF(2) output masks and phase polynomial mod 8 verify arbitrary live inputs and clean scratch. |

The clean-scratch action implements the CNOT-plus-phase representation used by
Amy, Maslov, and Mosca (arXiv:1303.2042). It is a limited reproduction rather
than a general matroid-partition/T-par synthesis engine. Existing wires are
arbitrary live inputs; added wires must start and finish in zero. It does not
infer cleanliness of an existing idle wire, reassign a data wire, or act across
Hadamards. Phase regions are rediscovered after each rewrite. Scratch wires
certified clean at the end of one local action form an explicit trailing pool
that later local actions may reuse; the trace records allocated, reused, and
released IDs. PyZX and Feynman whole-circuit actions explicitly invalidate that
pool and any semantic-boundary claim.

The pinned `feynopt` v0.1.0 release archive has SHA-256
`d3a8d15a4140f159ff87fbc982c7938b985a7ec735e7ac188254639c33b8de0a`.
The CLI advertises `-tpar` and `-mctExpand` but no scratch-allowance flag. The
`.qc` input format permits wires in `.v` omitted from `.i` and `.o` (clean
scratch). On a three-T parity block, `-tpar -verify` used two added wires but
both zero-scratch and two-scratch outputs had T-depth 1. On the seven-T CCZ
phase block, zero, two, and four scratch outputs all had T-depth 3, although
the latter used added wires. Its verifier accepts different ancilla sets with
matching primary inputs. Thus this release alone did not demonstrate a
workspace-for-depth gain on those diagnostics.

In the depth diagnostic, this pinned release also reported an internal
`Can't reify False + q1 = 0` error for some attempts to run T-par after the
local clean-scratch action. Those attempts fail without producing a selectable
circuit; they do not establish that Feynman can exploit the newly added scratch.

The local exact CCZ phase diagnostic has `(T,D,A)=(7,5,0)` before resynthesis.
One, two, and four clean scratch wires give `(7,4,1)`, `(7,2,2)`, and
`(7,1,4)` respectively, each checked against the construction target and the
canonical clean-input region contract. This is a diagnostic capability claim;
the measured study must determine applicability on approximate workloads.

In the historical synthetic development witness, PyZX optimization of the cap-4 HWP seed
changes `(190,73,7)` to `(176,114,7)`. Adaptive lookahead and the fixed-order
ablation both reach that endpoint, so this demonstrates an enabling
representation change but not an adaptive-priority advantage.
