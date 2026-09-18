# Problem Specification

## Observations

### O1: Search does not establish adaptive preference value
- **Statement**: Adaptive and frozen priorities tie on all five balanced development cases; the latest fixed count-then-depth sequence matches the discovered winner.
- **Evidence**: `evidence/results/iterative-ancilla.md`, `evidence/results/single-demonstration.md`.
- **Implication**: These experiments support useful construction/backend combinations, not a unique benefit from preference updates.

### O2: Workspace exchanges depth without improving count in the exact diagnostic
- **Statement**: The depth diagnostic contains Pareto points (7,3,0) and (7,1,4), with tuples ordered as T-count, T-depth, allocated clean ancillas.
- **Evidence**: `evidence/results/ancilla-depth.md`.
- **Implication**: Tradeoffs exist within the tested action space; this does not establish a new frontier over prior work.

## Gaps

### G1: New construction space remains untested
- **Statement**: No established novelty or resource-frontier improvement follows from these development studies.
- **Caused by**: O1, O2.
- **Existing attempts**: Established parity/HWP seeds, exact PyZX and optional Feynman passes, limited clean-scratch phase resynthesis.
- **Why they fail**: The studies cannot distinguish adaptive control as an enabling mechanism; they do not rule out different constructions.

### G2: Stronger execution models are not implemented
- **Statement**: Measurement-assisted cleanup and catalytic HWP are not eligible emitted competitors.
- **Caused by**: The declared unitary execution contract.
- **Existing attempts**: Source audits in the repository prior-work matrix.
- **Why they fail**: Paper-level estimates alone do not establish channel, error, catalyst restoration, and workspace equivalence.

## Key Insight
The evidence motivates testing a structural phase construction before expanding pass-order search. This is an AI recommendation under discussion, not an adopted project pivot or a new result.

## Assumptions
- Preserve exact affine-parity semantics, global phase, and clean-workspace restoration.
- Compare candidates with the same total operator-norm error and execution model.
- Development graphs and diagnostics are not held-out evaluation.
