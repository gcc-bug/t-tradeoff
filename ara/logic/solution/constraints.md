# Constraints and Known Limits

Source: `docs/semantics.md`, `docs/resource-model.md`, `docs/review-guide.md`, and the archived reports.

- The supported target is a diagonal affine-parity phase block. Controlled application and general commuting-Pauli diagonalization are outside the contract.
- Active constructions are unitary-only. Toffolis use the exact seven-T, three-T-layer decomposition, followed by full-stream scheduling.
- HWP with copied general predicates includes parity materialization, carry workspace, and reversed cleanup. Eligible distinct singleton inputs use an in-place layout and must be restored.
- Total approximation error is allocated across actual generic rotations. Exact rewrites must preserve the already lowered operator, including the repository global-phase convention.
- Workspace is allocated additional logical clean qubits, not a physical factory or general dirty-ancilla cost model.
- Local scratch reuse needs an explicit cleanup certificate. Whole-circuit PyZX invalidates scratch-pool metadata.
- The latest search retains only intermediates satisfying hard limits; it does not explore a path through temporarily infeasible states.
- Measurement/feed-forward, catalysts, physical runtime, factory throughput, routing, and code distance are excluded.
- Recorded development data establish neither held-out generalization nor novelty. Feynman availability differs between earlier recorded studies and the latest demonstration.
- Stored reports retain historical revision fingerprints. Initialization at the current HEAD does not relabel old results as reruns.
