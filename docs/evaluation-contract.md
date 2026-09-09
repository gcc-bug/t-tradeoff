# Evaluation Contract

## Common Target

Every compared method receives the same serialized `PhaseProgram`, exact angle
binding, block boundaries, `canonical-v2` preprocessing, total operator-norm
synthesis budget, workspace budget, gate model, application count, and
objective. Coefficients are exact integers and angle classes are joined by ID,
never approximate numeric equality.

## Evidence

Method metadata distinguishes a basic reference, correctness reference,
audited prior construction, diagnostic, equivalence demonstration, historical
estimate, unverified estimate, and unavailable method. Default eligibility is
an explicit field of that metadata; verification alone does not establish
competitive strength.

| Verification result | Default ranking consequence |
| --- | --- |
| `verified_lowered_dense` | Eligible when the method's evidence metadata allows it |
| `verified_lowered_compositional` | Eligible with scope shown; ideal semantics, primitive matrices, exact event binding, phase, and error allocation all passed |
| `lowered_evidence_unsupported` | Ineligible; a required proof connection was absent |
| `macro_not_verified` | Ineligible; a formula-level or measured macro remains |
| failure or unavailable | Ineligible |

Schema-v3 runs pair each result row with a checksummed circuit artifact. During
execution, construction and lowered semantics are verified and every accepted
external result is checked against its source. Stored-result verification
checks schema, row/artifact identity, checksum, recorded verification status,
error and resource limits, and finite metrics; it does not claim to re-execute
an external backend.

## Generation And Selection

Direct and shared-parity candidates are generated once. Ordinary HWP generates
documented batch limits from one through the configured cap and reevaluates
each full circuit with its actual rotation count under the same total error.

The search archive retains eligible nondominated `(T, T-depth, ancilla)` points.
Hard T-count, T-depth, and ancilla limits are applied without relaxation. If no
candidate passes them, the result is explicitly infeasible. Supported final
objectives are:

| Objective | Tie-break |
| --- | --- |
| `t_count` | T-depth, ancillas, stable ID |
| `t_depth` | T-count, ancillas, stable ID |
| `ancilla` | T-count, T-depth, stable ID |
| normalized balance | score, T-count, T-depth, ancillas, stable ID |

The normalized balance uses fixed positive configured references and
nonnegative weights. Backend time is a budget/accounting field, not an
optimization objective.

## Reporting

Rows report the selected implementation, total T, scheduled T-depth, peak
allocated workspace, objective value, synthesis error, verification scope,
backend calls/time, rejection counts, decision trace, and Pareto endpoints.
Scheduling uses the emitted dependency stream; stage depths are not added.

The default study separates explanatory, negative-control, and public
development inputs. The QED-C and adaptive synthetic cases are not held-out
evidence. Removed, measured, catalytic, and unavailable methods do not enter the
comparison.
