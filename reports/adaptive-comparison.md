# Adaptive Resource Tradeoff Study

Results: `results/raw/adaptive-comparison`

Code revision: `7ccfbeaf55820feac4fbd2b7098538fad9346df8`. Config hash: `41636a876c763ad223b042e1bc6f0dc628b864865e179d5ad7abbc5848591bfe`. Manifest hash: `528371eea56f5e42df2d6c5b6d7ff5e757dcf516d4ef298249d803dc04c03772`.

Fixed final objective: `{"mode": "balance", "references": {"ancilla": 8.0, "t_count": 200.0, "t_depth": 200.0}, "weights": {"ancilla": 0.05, "t_count": 0.9, "t_depth": 0.05}}`. Hard limits: `{"ancilla": 8, "t_count": 400, "t_depth": 300}`.

## Integrated Methods

| Backend | Revision | Status | Detail |
| --- | --- | --- | --- |
| feynman | v0.1.0@2b52a0a78c10999cfc4c1d9c76c994c471cf2350 | available | phasefold, tpar |
| ncf | n/a | unsupported | no public artifact located |
| pyzx | 0.9.0 | available | exact API |
| trasyn | n/a | out_of_scope | approximate resynthesis requires error reallocation |

Unsupported, timed-out, and verification-inconclusive outputs are not treated as feasible alternatives.

## Policy Outcomes

`Resources` is `(T, scheduled T-depth, peak allocated workspace)`. The objective and tie-breaks remain fixed across every row.

| Case | Workspace budget | Policy | Status | Resources | J | Evaluations | Backend calls | Backend seconds |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| hwp_joint_optimization_witness | 8 | adaptive | success | (200, 50, 0) | 0.9125 | 10 | 4 | 3.592687 |
| hwp_joint_optimization_witness | 8 | adaptive_lookahead | success | (176, 114, 7) | 0.8642500000000001 | 10 | 4 | 1.389833 |
| hwp_joint_optimization_witness | 8 | fixed_order | success | (176, 114, 7) | 0.8642500000000001 | 10 | 4 | 1.071564 |
| hwp_joint_optimization_witness | 8 | static_ancilla | success | (200, 50, 0) | 0.9125 | 10 | 4 | 3.523164 |
| hwp_joint_optimization_witness | 8 | static_balanced | success | (200, 50, 0) | 0.9125 | 8 | 2 | 2.186791 |
| hwp_joint_optimization_witness | 8 | static_count_ancilla | success | (200, 50, 0) | 0.9125 | 7 | 1 | 0.083448 |
| hwp_joint_optimization_witness | 8 | static_count_depth | success | (200, 50, 0) | 0.9125 | 7 | 1 | 0.082460 |
| hwp_joint_optimization_witness | 8 | static_depth | success | (200, 50, 0) | 0.9125 | 10 | 4 | 3.430036 |
| hwp_joint_optimization_witness | 8 | static_t | success | (200, 50, 0) | 0.9125 | 10 | 4 | 3.388501 |
| hwp_joint_optimization_witness | 8 | static_t_lookahead | success | (200, 50, 0) | 0.9125 | 10 | 4 | 0.846259 |
| weighted_no_collective_group | 8 | adaptive | success | (254, 252, 0) | 1.206 | 7 | 4 | 11.358829 |
| weighted_no_collective_group | 8 | adaptive_lookahead | success | (254, 252, 0) | 1.206 | 7 | 4 | 4.543268 |
| weighted_no_collective_group | 8 | fixed_order | success | (254, 252, 0) | 1.206 | 7 | 4 | 3.552893 |
| weighted_no_collective_group | 8 | static_ancilla | success | (254, 252, 0) | 1.206 | 7 | 4 | 10.400012 |
| weighted_no_collective_group | 8 | static_balanced | success | (254, 252, 0) | 1.206 | 5 | 2 | 6.333941 |
| weighted_no_collective_group | 8 | static_count_ancilla | success | (254, 252, 0) | 1.206 | 4 | 1 | 0.426455 |
| weighted_no_collective_group | 8 | static_count_depth | success | (254, 252, 0) | 1.206 | 4 | 1 | 0.436172 |
| weighted_no_collective_group | 8 | static_depth | success | (254, 252, 0) | 1.206 | 7 | 4 | 9.899157 |
| weighted_no_collective_group | 8 | static_t | success | (254, 252, 0) | 1.206 | 7 | 4 | 9.360048 |
| weighted_no_collective_group | 8 | static_t_lookahead | success | (254, 252, 0) | 1.206 | 7 | 4 | 8.833852 |

Against the best fixed-priority endpoint, adaptive lookahead has 1 wins, 1 ties, and 0 regressions on 2 matched feasible cases. Against the best nonadaptive endpoint including fixed order, it has 0 wins, 2 ties, and 0 regressions on 2 cases. Backend calls are shown per row; the static weight multi-start budget is split across its predeclared vectors.

## Paired Optimization

These are accepted backend steps only; construction-seed transitions are listed separately in the decision trace.

| Case | Workspace budget | Policy | Backend action | Before | After |
| --- | ---: | --- | --- | --- | --- |
| hwp_joint_optimization_witness | 8 | adaptive_lookahead | pyzx:zx_extract | (190, 73, 7) | (176, 114, 7) |
| hwp_joint_optimization_witness | 8 | fixed_order | pyzx:zx_extract | (190, 73, 7) | (176, 114, 7) |
| weighted_no_collective_group | 8 | adaptive | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | adaptive_lookahead | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | fixed_order | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | static_ancilla | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | static_balanced | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | static_count_ancilla | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | static_count_depth | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | static_depth | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | static_t | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group | 8 | static_t_lookahead | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |

## Decision Trace

| Step | Region | Action/backend | Reason | Priority | T | D | A | J | Evaluations | Seconds | State |
| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |
| 1 | whole_circuit | construction:hwp_adder_unitary:adder_compressor_unitary_cap_4 | construction seed exposes a supported exact backend opportunity | 2.3879 | 200 -> 190 | 50 -> 73 | 0 -> 7 | 0.9125 -> 0.917 | 6 | 0.000000 | provisional |
| 2 | whole_circuit | pyzx:zx_extract | count has weight/pressure 1.400 and 281 scheduled events have T-slack; 6 logical Toffolis expose a joint exact-simplification opportunity | 2.3879 | 190 -> 176 | 73 -> 114 | 7 -> 7 | 0.917 -> 0.86425 | 10 | 1.389833 | accepted |

## Final Pareto Points

| Case | Workspace budget | T | D | A | Implementations |
| --- | ---: | ---: | ---: | ---: | --- |
| hwp_joint_optimization_witness | 8 | 176 | 114 | 7 | hwp_adder_unitary:adder_compressor_unitary_cap_4\|pyzx:zx_extract |
| hwp_joint_optimization_witness | 8 | 190 | 73 | 7 | hwp_adder_unitary:adder_compressor_unitary_cap_4 |
| hwp_joint_optimization_witness | 8 | 200 | 50 | 0 | hwp_adder_unitary:adder_compressor_unitary_cap_1, hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:todd, hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract, independent:normalized_independent, independent:normalized_independent\|feynman:phasefold, independent:normalized_independent\|pyzx:todd, independent:normalized_independent\|pyzx:zx_extract, shared_parity:normalized_greedy_anchor_walk |
| weighted_no_collective_group | 8 | 254 | 252 | 0 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract, independent:normalized_independent\|pyzx:zx_extract, shared_parity:normalized_greedy_anchor_walk\|pyzx:zx_extract |

## Mechanism Conclusion

At least one accepted sequence crosses a temporarily worse construction state before exact joint optimization improves the fixed final objective. The best nonadaptive policy matches or beats every adaptive endpoint, so these rows do not establish an adaptive-priority advantage.

Post-optimization T is reported only as a total because optimized gates no longer have a reliable arithmetic-versus-rotation attribution.

Recorded statuses: `success`=20.
