# Interleaved HWP development comparison

Same staged/readiness constructions, precision policy and complete-wave model. Each query pays its declared wall-clock budget; the first pays input loading and setup. Cold runs the first query; warm runs both with caches shared only inside that trial. All incumbents are emitted and verified. These are development inputs, not holdouts.

| Mode | Budget/query s | Method | Certified optimum / queries | Verified incumbent / queries | Median trial s |
|---|---:|---|---:|---:|---:|
| cold | 1 | serial_graph | 12 / 18 | 18 / 18 | 0.6649 |
| cold | 1 | serial_transfer | 12 / 18 | 18 / 18 | 0.4451 |
| cold | 1 | upfront | 12 / 18 | 18 / 18 | 0.3804 |
| cold | 1 | interleaved | 15 / 18 | 18 / 18 | 0.3840 |
| cold | 1 | interleaved_coupled | 15 / 18 | 18 / 18 | 0.3843 |
| cold | 1 | upfront_coupled | 12 / 18 | 18 / 18 | 0.3876 |
| cold | 1 | batching | 0 / 18 | 15 / 18 | 0.6858 |
| cold | 3 | serial_graph | 15 / 18 | 18 / 18 | 0.4572 |
| cold | 3 | serial_transfer | 15 / 18 | 18 / 18 | 0.4523 |
| cold | 3 | upfront | 15 / 18 | 18 / 18 | 0.3861 |
| cold | 3 | interleaved | 18 / 18 | 18 / 18 | 0.3689 |
| cold | 3 | interleaved_coupled | 18 / 18 | 18 / 18 | 0.3869 |
| cold | 3 | upfront_coupled | 15 / 18 | 18 / 18 | 0.3907 |
| cold | 3 | batching | 0 / 18 | 18 / 18 | 0.7023 |
| warm | 1 | serial_graph | 24 / 36 | 36 / 36 | 0.4763 |
| warm | 1 | serial_transfer | 24 / 36 | 36 / 36 | 0.4766 |
| warm | 1 | upfront | 27 / 36 | 36 / 36 | 0.4147 |
| warm | 1 | interleaved | 30 / 36 | 36 / 36 | 0.3804 |
| warm | 1 | interleaved_coupled | 30 / 36 | 36 / 36 | 0.4001 |
| warm | 1 | upfront_coupled | 27 / 36 | 36 / 36 | 0.4186 |
| warm | 1 | batching | 0 / 36 | 30 / 36 | 0.7637 |
| warm | 3 | serial_graph | 30 / 36 | 36 / 36 | 0.4780 |
| warm | 3 | serial_transfer | 30 / 36 | 36 / 36 | 0.4932 |
| warm | 3 | upfront | 30 / 36 | 36 / 36 | 0.4140 |
| warm | 3 | interleaved | 33 / 36 | 36 / 36 | 0.3856 |
| warm | 3 | interleaved_coupled | 33 / 36 | 36 / 36 | 0.4208 |
| warm | 3 | upfront_coupled | 30 / 36 | 36 / 36 | 0.4291 |
| warm | 3 | batching | 0 / 36 | 36 / 36 | 0.7572 |

Batching is a restricted reference family: its completion does not certify the full-family optimum. Missing verified incumbents include exhausted budgets during setup or before final verification. Mixed completion counts are not equal-quality speedups.

| Fixed-budget pair: interleaved_coupled vs upfront_coupled | Better U | Equal U | Worse U | Only interleaved feasible | Only upfront feasible | Neither feasible |
|---|---:|---:|---:|---:|---:|---:|
| cold, 1s | 3 | 15 | 0 | 0 | 0 | 0 |
| cold, 3s | 3 | 15 | 0 | 0 | 0 | 0 |
| warm, 1s | 3 | 33 | 0 | 0 | 0 | 0 |
| warm, 3s | 3 | 33 | 0 | 0 | 0 | 0 |

| Separate reference | Query | Full-family best (complete?) | Strong batching best (complete?) | One local optimum/group (complete?) |
|---|---|---|---|---|
| native_3 | count | (108, 54, 1) (True) | (108, 54, 1) (True) | (108, 54, 1) (True) |
| native_3 | constrained_count | (108, 54, 1) (True) | (108, 54, 1) (True) | (108, 54, 1) (True) |
| native_6 | count | (204, 68, 4) (True) | (204, 68, 4) (True) | (204, 68, 4) (True) |
| native_6 | constrained_count | (228, 56, 2) (True) | (228, 56, 2) (True) | (228, 56, 2) (True) |
| native_7 | count | (204, 68, 4) (True) | (204, 68, 4) (True) | (204, 68, 4) (True) |
| native_7 | constrained_count | (284, 58, 2) (True) | (284, 58, 2) (True) | (284, 58, 2) (True) |
| native_9 | count | (468, 468, 0) (False) | (468, 52, 0) (False) | (468, 52, 0) (False) |
| native_9 | constrained_count | (354, 58, 3) (True) | (468, 52, 0) (False) | (354, 58, 3) (True) |
| groups_3_2 | count | (210, 56, 1) (True) | (210, 56, 1) (True) | (210, 56, 1) (True) |
| groups_3_2 | constrained_count | (210, 56, 1) (True) | (210, 56, 1) (True) | (210, 56, 1) (True) |
| overlapping_6 | count | (228, 112, 4) (True) | (228, 112, 4) (True) | (228, 112, 4) (True) |
| overlapping_6 | constrained_count | (284, 166, 3) (True) | (312, 156, 0) (True) | None (True) |

Maximum measured deadline overrun: 0.0405s. Atomic synthesis/verification and descriptor initialization can overrun and are charged.

Raw records include L/U, plans, fingerprints, first incumbent/improvement, graph and recipe counts, evaluations, refinements, queue sizes, partial waves, setup time and actual elapsed time. Separate longer references and local-choice diagnostics are never supplied to timed searches.

This experiment changes evaluation and search, not the arithmetic family. Any fixed-budget quality advantage is controller performance; any completed full-family result shared with batching is not a new circuit-family gain. No published-method superiority or within-block release/reuse claim follows.
