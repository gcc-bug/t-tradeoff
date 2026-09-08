# Evaluation Contract

## Common target

Every compared method receives the same serialized PhaseProgram, exact angle
binding, block boundaries, canonical-v2 preprocessing, total operator-norm
synthesis budget, workspace budget, gate model, application count, and
objective. Coefficients are exact integers and angle classes are joined by ID,
never approximate numeric equality.

The primary metrics are T-count, scheduled logical T-depth, and peak extra
logical qubits. The schedule is a valid emitted dependency schedule, not an
optimal-depth or minimum-workspace claim.

## Evidence levels

| Evidence | Meaning | Primary ranking |
| --- | --- | --- |
| verified_lowered_dense | Macro-free gate stream passes clean-input isometry spectral-norm comparison | Eligible |
| verified_lowered_compositional | Dense allocation exceeded the declared cap; deterministic replay, primitive validation, transformation certificate, and synthesis bound pass | Eligible with scope shown |
| macro_not_verified | At least one arithmetic or measured channel remains a formula-level macro | Ineligible |
| unavailable or failure | Matching implementation or evidence is absent | Ineligible |

An emitted method cannot contain a MacroEvent. Hash integrity alone never
qualifies evidence. A schema-v2 replay reconstructs the program, compiler
candidate, rotations, gate stream, error bound, and resource record.

## Selection

HWP batch limits from one through the configured search cap are compiled and
fully lowered under the same whole-circuit error budget. The selected triple
method similarly compares the raw rewrite, independent synthesis, and
shared-parity synthesis. T-count selection uses T-count, then T-depth, peak
workspace, and a stable label as tie-breaks. T-depth reverses the first two
criteria. Pareto mode accepts the preferred rewrite only when it dominates or
ties all eligible alternatives; otherwise it falls back.

All alternatives, failures, resource tuples, and the nondominated set are
stored. Estimated macros cannot enter an emitted selection pool.

## Pairing and strata

A comparison key includes target and input hashes, semantic and preprocessing
profiles, exact angle expression, error budget and metric, reuse count,
workspace, gate model, code revision, configuration hash, objective, and
benchmark stratum. Duplicate method rows for one key are rejected.

Public, synthetic-diagnostic, and negative-control populations are reported
separately. Each named baseline gets its own win, tie, regression, and matched
denominator counts. Zero-T baselines are counted explicitly. A best-strong
comparison is reported only when at least one eligible strong baseline exists.

The emitted ANF HWP is a correctness reference, not a competitive reproduction
of published in-place or measurement-assisted HWP. Catalytic, measured, and
joint-synthesis methods remain outside primary claims until their channels and
matching resource assumptions are implemented and verified.
