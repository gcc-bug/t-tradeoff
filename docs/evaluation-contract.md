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

Schema-v4 result rows pair each result with a checksummed circuit artifact. During
execution, construction and lowered semantics are verified and every accepted
external result is checked against its actual verified parent chain. Stored-result
verification replays the saved construction-to-selected proof chain, recounts
the selected gates and every reported Pareto circuit, and checks schema,
checksums, error and resource limits. It does not rerun backend optimization
or verify unreported archive items.

## Generation And Selection

Direct and shared-parity candidates are generated once. Ordinary HWP generates
documented batch limits from one through the configured cap and reevaluates
each full circuit with its actual rotation count under the same total error.

The search archive retains verified feasible circuits; reporting takes the
nondominated `(T, T-depth, ancilla)` points. Every policy begins with the same
verified construction seeds and the same available exact actions. The search
also retains bounded, structurally distinct, temporarily worse alternatives
for additional transformations. Static-preference and fixed-sequence portfolios
split a single call budget and a single search-time allowance between their
respective policies; root preparation is charged once per portfolio.
For each workspace-budget row, the active ancilla limit is the smaller of that
budget and the configured hard ancilla limit; a zero-budget row cannot allocate
scratch during search.
Hard T-count, T-depth, and ancilla limits are applied without relaxation. If no
seed passes them, the result says no feasible seed found under this search
policy; it is not a mathematical infeasibility proof. Supported final
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
backend calls/time, root preparation time, rejection counts, attempt trace,
and Pareto endpoints with replayable circuits in their checksummed artifacts.
Verified outputs rejected by a hard limit retain their measured costs in the
trace. Search wall time includes backend, verification, and
controller work; backend execution is a subset and is not added again.
PyZX optimization runs in a bounded worker, and Feynman subprocesses receive
the remaining deadline. Failed, timed-out, and inconclusive calls consume their
budget; a timed-out circuit cannot enter the archive.
Scheduling uses the emitted dependency stream; stage depths are not added.

The default study separates explanatory, negative-control, and public
development inputs. The QED-C and adaptive synthetic cases are not held-out
evidence. Removed, measured, catalytic, and unavailable methods do not enter the
comparison.
