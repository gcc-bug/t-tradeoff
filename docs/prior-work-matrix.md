# Prior Work Matrix

Audit date: 2026-09-09. A citation is not treated as coverage: each row records
the exact version, adapter boundary, validation, and remaining limitation.

| Method/source | Supported input and gate model | Adapter and code/license status | Validation and remaining limitation |
| --- | --- | --- | --- |
| Ross-Selinger, arXiv:1403.2975v3; `pygridsynth==2.0.0` | One generic `Rz`; ancilla-free Clifford+T; operator-norm tolerance | Pinned Python package; its `Rz` output is adapted to `P(theta)` with explicit global phase | Every returned matrix and error is recomputed; this is a single-rotation backend, not collective synthesis |
| Gidney, arXiv:1709.06648v3, Figs. 2-3 and Hamming-weight example | Temporary logical AND; four-T compute, measured Clifford fixup/uncompute | Paper circuit audited; no measured adapter is eligible | Unit tests cover the unitary Toffoli substitute only; measurement branches and feedforward channel remain unimplemented |
| Kivlichan et al., arXiv:1902.10673v4, Appendix A.1 | Equal-angle parallel rotations; staged HWP; measured cleanup; bounded batching | Local `hwp_adder_unitary` emits the adders and substitutes reversed 7-T Toffolis for cleanup | Truth tables and sizes 1-8 verified; resources come from the emitted stream. This is a unitary adaptation, not the published measured cost |
| Amy-Maslov-Mosca T-par; Feynman `v0.1.0` at `2b52a0a...` | Fully emitted Clifford+T `.qc`; all wires declared as primary input/output | Thin subprocess adapter; BSD-2-Clause release binary exercised with `-tpar -verify` | Independent PyZX equivalence and phase correction follow the backend check; T-par changes depth and may substantially increase CNOT count |
| Amy-Lunderville relational phase folding; Feynman `d2c382a...` | Current source advertises `-apf`, `-qpf`, and `-ppf` for QASM and `.qc` | Thin adapter accepts the advertised actions, but no current executable was built | Cabal/GHC are absent and no current binary release exists, so relational-analysis results are `unsupported`, not ranked |
| PyZX `0.9.0`, Apache-2.0 | Fully emitted Clifford+T stream | Python adapter exposes basic cancellation, TODD phase-block optimization, and full ZX reduction/extraction | Every accepted output passes source/result ZX equivalence; an explicit scalar correction preserves the repository's global-phase convention |
| Qualtran `HammingWeightCompute`, revision `d5faa99db850001d440d0cc4e05b7b20b249a652` | Out-of-place Hamming weight using temporary ANDs | Apache-2.0 source inspected; no code copied or runtime dependency added | Corroborates the staged compressor order and `n-popcount(n)` count; register layout differs from the local in-place-on-parities adaptation |
| Kan-Symons, arXiv:2411.02160v2, "Space-time trade-off in Hamming-weight phasing" and Supplementary Fig. 3 | Equal-angle HWP; generalized phase gradient; angle-specific reusable catalyst; measured cleanup | Paper formulas only; local legacy macro remains unverified and excluded | Audit records catalyst preparation, restoration, extra `floor(log2 M)+1` Toffolis, and repeated-use requirement; no channel/catalyst validation exists |
| Gidney-Fowler, arXiv:1812.01238v3, phase-catalysis circuits | Catalyst-assisted production and generalized phase-catalysis assumptions | Paper only in this repository | Catalyst cannot be modeled as a clean ancilla; preparation, correlated error, and restoration remain open obligations |
| Rustiq, revision `425000222e21a7a28d70a08c75be968f16fd6903` | Pauli/parity-network optimization, primarily two-qubit gate objectives | Public implementation pointer audited; compatibility adapter not integrated | Could answer a future CNOT-network question, but is not currently evidence for collective T-count improvement |
| Li et al., arXiv:2510.13573v1, Non-Clifford Fusion | Joint synthesis of small transformed Pauli groups under its reported tolerances | Compatible public artifact and license not confirmed; method reports `unavailable` | Precision and target adapters remain unresolved; it is not included in rankings |
| Hao-Xu-Tannu Trasyn, arXiv:2503.15843v2; `ab5183c...` | Approximate single-qubit `U3`/`Rz` synthesis; optional Qiskit circuit preprocessing | MIT implementation found and interface inspected | Our initial pipeline has one controlled approximate `Rz` stage followed by exact rewrites. Replacing exact Clifford+T regions with separately approximate U3 results would require a new error allocation, so Trasyn is not an eligible action in this milestone |

The tracked QED-C inputs use revision
`feb22a900d9d94d40e81bc1d25e149bd8f3cbc18` under Apache-2.0. They are
development data because they influenced earlier investigation. HamLib remains
unintegrated pending subset and license review.

NCF repository search by title returned no public implementation on the audit
date. This is an artifact-availability result, not evidence about NCF quality.
