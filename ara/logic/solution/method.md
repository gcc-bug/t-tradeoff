# Implemented Pipeline

Source: repository README and `docs/review-guide.md`; code entry points are indexed in `src/artifacts.md`.

Normalize each PhaseProgram with common exact-angle, multiplicity, offset, and block semantics. Emit independent parity phases, shared-parity walks, and feasible batched unitary HWP constructions. Verify the ideal construction, lower generic rotations under one total error budget, and verify the lowered operator and workspace behavior.

Apply bounded exact PyZX, optional Feynman, and limited clean-scratch phase-region rewrites. Check each accepted child against its verified parent, reschedule the emitted circuit, and rank against one immutable final objective and hard limits. Keep emitted Pareto circuits and proof chains. Fixed sequences and frozen priorities are controls on the interpretation of discovery.

The latest demonstration adds targeted critical/slack regions and explicit scratch-pool accounting. Its fixed reference attains the discovered endpoint without requiring reuse. This does not erase the implementation's certified reuse behavior; it limits the claim that reuse enabled the result.
