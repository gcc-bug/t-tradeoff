# Experiment Summary

Results: `results/raw/pilot-initial`

This is prototype evidence, not a novelty or performance claim. Emitted and macro-estimated counts are separated.

## Status

- `infeasible`: 2
- `success`: 50

## Resource overview

| Method | Accounting | Rows | Mean T-count | Min T-count | Max T-count |
| --- | --- | ---: | ---: | ---: | ---: |
| dependent_triples | emitted | 13 | 304.15 | 58 | 624 |
| hwp | estimated_macro | 11 | 367.82 | 108 | 718 |
| independent | emitted | 13 | 385.85 | 150 | 840 |
| shared_parity | emitted | 13 | 385.85 | 150 | 840 |

## Candidate comparison

Against the best fully emitted independent/shared-parity baseline on paired unitary rows: 6 wins, 7 ties, 0 losses.
Mean paired T-count ratio: 0.8110.

Catalyzed rows include preparation plus the declared number of applications. `amortized_t` divides total T-count by reuse count; composed T-depth is not amortized.

## Four-part assessment

- Observation: exact dependent triples occur in some diagnostics and graph triangles; HWP arithmetic cost is nonzero and separately reported.
- Gap: this run does not establish that production HWP or joint-synthesis tools fail to recognize the same identity.
- Verification: emitted rows passed exact basis checks; macro rows passed ideal-macro semantics only. Small coherent-state, per-rotation synthesis, and stored-artifact checks were applied where relevant.
- Potential: continue only if generic-angle pilot wins survive stronger emitted HWP and NCF baselines on independently selected public cases.
