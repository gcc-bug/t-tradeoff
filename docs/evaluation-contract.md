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

Schema-v2 replay reconstructs the target, candidate, rotations, emitted stream,
error bound, tradeoff decomposition, resources, evidence metadata, limits, and
selection artifacts. Hash integrity alone does not qualify evidence.

## Generation And Selection

Direct and shared-parity candidates are generated once. Ordinary HWP generates
documented batch limits from one through the configured cap and reevaluates
each full circuit with its actual rotation count under the same total error.

The selector retains every eligible nondominated `(T, T-depth, ancilla)` point.
Hard T-count, T-depth, and ancilla limits are applied without relaxation. If no
candidate passes them, the result is `no feasible alternative`. The supported
objectives and tie-breaks are:

| Objective | Tie-break |
| --- | --- |
| `t_count` | T-depth, ancillas, stable ID |
| `t_depth` | T-count, ancillas, stable ID |
| `ancilla` | T-count, T-depth, stable ID |

Weighted sums and compilation time are not optimization objectives.

## Reporting

Rows report method and variant, generic rotations, arithmetic T, rotation T,
total T, scheduled T-depth, peak ancillas, synthesis error, verification scope,
and evidence provenance. Scheduling uses the emitted dependency stream; stage
depths are not added separately.

The default study separates explanatory, negative-control, and public
development inputs. The QED-C cases are not held-out evidence. ANF,
dependent-triple, legacy, measured, catalytic, and unavailable methods do not
enter the default comparison.
