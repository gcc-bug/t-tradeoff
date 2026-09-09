# Methodology Overview

The current milestone compares constructions, not candidate identities. Every
method receives one canonical `PhaseProgram`, exact angle binding, total
operator-norm error budget, workspace limit, and gate model.

## Construct

`preprocess` normalizes affine predicates, exact duplicates, coefficients, and
block-local angle groups once. `independent` is the direct rotation reference;
`shared_parity` changes only the parity network; `hwp_adder_unitary` exchanges
equal-angle rotations for an emitted staged compressor network. HWP batch
limits from one to the configured cap are generated before objective selection.

The old ANF popcount is a small correctness reference. The dependent-triple
methods demonstrate one special identity and its HWP equivalence. Legacy and
catalytic macros are formula evidence. None is a default competitor.

## Check And Count

Ideal construction verification checks the phase on every basis state up to
the declared limit and requires data and clean workspace restoration. Lowered
verification independently checks rotation matrices, a hard-coded Toffoli
decomposition matrix, deterministic event-to-operation binding, global phase,
and the exact allocation of local errors into the circuit budget. If those
obligations are absent, a memory cap produces an unsupported result rather than
a successful compositional certificate.

Resource accounting schedules dependencies in the actual emitted event stream.
The report separates arithmetic T from rotation T, and reports total T,
scheduled T-depth, peak extra qubits, error bound, and verification scope.

## Compare

Only emitted, ideal-verified, and lowered-verified alternatives carrying
explicit evidence metadata enter the default comparison. The selector retains
all nondominated `(T, T-depth, ancilla)` points, applies hard limits without
relaxation, and uses these policies:

| Objective | Primary metric | Tie-break |
| --- | --- | --- |
| `t_count` | T-count | T-depth, ancillas, stable ID |
| `t_depth` | scheduled T-depth | T-count, ancillas, stable ID |
| `ancilla` | peak extra qubits | T-count, T-depth, stable ID |

Changing the objective selects among generated circuits; it does not create a
new circuit. Weighted sums are intentionally absent.

The default fixed study is defined by `configs/default-study.yaml` and
`data/manifests/refocus-study.yaml`. Its three QED-C graphs are public
development inputs, not held-out evidence. See `reports/default-study.md` for
the result and `docs/review-guide.md` for the shortest code-reading path.
