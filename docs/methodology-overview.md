# Methodology Overview

The current milestone asks whether state-dependent optimization priorities add
value when the user's final objective stays fixed. Every policy receives the
same canonical `PhaseProgram`, exact angle binding, total operator-norm error
budget, workspace limit, construction seeds, available backend actions, and
gate model.

## Construct

`preprocess` normalizes affine predicates, exact duplicates, coefficients, and
block-local angle groups once. `independent` is the direct rotation reference;
`shared_parity` changes only the parity network; `hwp_adder_unitary` exchanges
equal-angle rotations for an emitted staged compressor network. HWP batch
limits from one to the configured cap are generated before objective selection.

Retired ANF, dependent-triple, legacy-macro, and catalytic-estimate code remains
only in Git history. Historical reports and the HWP audit preserve the useful
facts without presenting those implementations as competitors.

## Check And Count

Ideal construction verification checks the phase on every basis state up to
the declared limit and requires data and clean workspace restoration. Lowered
verification independently checks rotation matrices, a hard-coded Toffoli
decomposition matrix, deterministic event-to-operation binding, global phase,
and the exact allocation of local errors into the circuit budget. If those
obligations are absent, a memory cap produces an unsupported result rather than
a successful compositional certificate.

Resource accounting schedules dependencies in the actual emitted event stream,
records critical T events and event slack, and derives peak workspace from
allocated wires. Post-optimization T is reported as a total because its former
arithmetic/rotation attribution is no longer reliable.

## Compare

Only emitted, ideal-verified, and lowered-verified alternatives enter search.
The final objective is either a constrained single metric or

```text
J = wT*T/Tref + wD*D/Dref + wA*A/Aref,
```

with nonnegative weights and fixed positive references. Hard limits and
tie-breaks remain unchanged throughout a run. Ancilla-first requires explicit
T-count and T-depth limits.

Static priorities, a fixed pass order, adaptive priorities without lookahead,
and adaptive/fixed-priority two-action lookahead share construction seeds and
bounded backend calls. The controller uses the incumbent's constraint pressure,
plus source schedule and algebraic evidence, to rank supported actions. A
provisional construction may worsen `J`, but only a verified backend endpoint
that improves the fixed objective is accepted.

| Single objective | Primary metric | Tie-break |
| --- | --- | --- |
| `t_count` | T-count | T-depth, ancillas, stable ID |
| `t_depth` | scheduled T-depth | T-count, ancillas, stable ID |
| `ancilla` | peak extra qubits | T-count, T-depth, stable ID |

The default fixed study retains four controls and three checksum-pinned QED-C
graphs, all development data. The adaptive comparison contains one synthetic
mechanism witness and one weighted negative control selected before the final
run; both were used during controller development. No additional public QED-C
subset could be frozen independently because the repository contains only the
three already-used inputs and no new dataset acquisition was justified during
this bounded milestone. Consequently the adaptive result is a reproducible
synthetic diagnosis, not held-out or general evidence.

On the witness, adaptive lookahead and fixed order both reach the verified
`(176,114,7)` endpoint. This supports the representation-changing mechanism but
does not show that adaptive priority outperforms a strong fixed order.
