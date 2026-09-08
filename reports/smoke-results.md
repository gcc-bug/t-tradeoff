# Experiment Summary

> Historical prototype evidence from schema v1. These rows are excluded from
> repaired primary comparisons.

Results: `results/raw/smoke`

This is prototype evidence, not a novelty or performance claim. Emitted and macro-estimated counts are separated.

## Status

- `infeasible`: 9
- `success`: 27
- `unavailable`: 6

## Resource overview

| Method | Accounting | Rows | Mean T-count | Min T-count | Max T-count |
| --- | --- | ---: | ---: | ---: | ---: |
| catalyzed_hwp | estimated_macro | 6 | 199.00 | 37 | 361 |
| dependent_triples | emitted | 6 | 6.67 | 3 | 14 |
| hwp | estimated_macro | 3 | 15.00 | 15 | 15 |
| independent | emitted | 6 | 3.00 | 3 | 3 |
| shared_parity | emitted | 6 | 3.00 | 3 | 3 |

## Candidate comparison

Against the best fully emitted independent/shared-parity baseline on paired unitary rows: 0 wins, 4 ties, 2 losses.
Mean paired T-count ratio: 2.2222.

Catalyzed rows include preparation plus the declared number of applications. `amortized_t` divides total T-count by reuse count; composed T-depth is not amortized.

## Four-part assessment

- Observation: exact dependent triples occur in some diagnostics and graph triangles; HWP arithmetic cost is nonzero and separately reported.
- Gap: this run does not establish that production HWP or joint-synthesis tools fail to recognize the same identity.
- Verification: emitted rows passed exact basis checks; macro rows passed ideal-macro semantics only. Small coherent-state, per-rotation synthesis, and stored-artifact checks were applied where relevant.
- Potential: continue only if generic-angle pilot wins survive stronger emitted HWP and NCF baselines on independently selected public cases.
