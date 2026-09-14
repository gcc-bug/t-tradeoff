# Adaptive Resource Tradeoff Study

Results: `results/raw/iterative-ancilla`

Code revision: `4d84d70ba17f012dd4c0023701073dd9213de1d1+dirty:875d5cf92434`. Config hash: `977b1bc43674bb9dc1b0442f3880ad93d160c2d72d5d2c140d44e0876be10f86`. Manifest hash: `8852bb02b4721cc4afbf7ef084101215697c531f62eb838c8578728b67a43ad8`.

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

`Resources` is `(T, scheduled T-depth, allocated logical ancillas)`. The objective and tie-breaks remain fixed across every row.

| Case | Angle | Workspace budget | Policy | Status | Resources | J | Calls | Total seconds |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: |
| exact_ccz_phase_diagnostic | theta_exact | 8 | adaptive | success | (7, 4, 0) | 0.0325 | 12 | 1.989 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | fixed_count_depth | success | (7, 4, 0) | 0.0325 | 6 | 0.830 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | fixed_depth_count | success | (7, 5, 0) | 0.03275 | 6 | 0.133 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | frozen | success | (7, 4, 0) | 0.0325 | 12 | 1.727 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | static_ancilla | success | (7, 3, 0) | 0.03225 | 3 | 0.144 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | static_balanced | success | (7, 4, 0) | 0.0325 | 3 | 0.266 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | static_depth | success | (7, 3, 0) | 0.03225 | 3 | 0.126 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | static_t | success | (7, 4, 0) | 0.0325 | 3 | 0.140 |
| hwp_joint_optimization_witness | theta_0173 | 8 | adaptive | success | (176, 112, 7) | 0.86375 | 12 | 10.587 |
| hwp_joint_optimization_witness | theta_0173 | 8 | fixed_count_depth | success | (176, 114, 7) | 0.8642500000000001 | 6 | 2.954 |
| hwp_joint_optimization_witness | theta_0173 | 8 | fixed_depth_count | success | (200, 50, 0) | 0.9125 | 6 | 1.759 |
| hwp_joint_optimization_witness | theta_0173 | 8 | frozen | success | (176, 112, 7) | 0.86375 | 12 | 8.678 |
| hwp_joint_optimization_witness | theta_0173 | 8 | static_ancilla | success | (200, 50, 0) | 0.9125 | 2 | 15.132 |
| hwp_joint_optimization_witness | theta_0173 | 8 | static_balanced | success | (176, 114, 7) | 0.8642500000000001 | 3 | 2.637 |
| hwp_joint_optimization_witness | theta_0173 | 8 | static_depth | success | (200, 50, 0) | 0.9125 | 1 | 15.138 |
| hwp_joint_optimization_witness | theta_0173 | 8 | static_t | success | (200, 50, 0) | 0.9125 | 3 | 1.419 |
| overlapping_phase_dependencies | theta_0173 | 8 | adaptive | success | (176, 111, 7) | 0.8635 | 12 | 10.098 |
| overlapping_phase_dependencies | theta_0173 | 8 | fixed_count_depth | success | (176, 157, 7) | 0.875 | 6 | 3.357 |
| overlapping_phase_dependencies | theta_0173 | 8 | fixed_depth_count | success | (190, 73, 7) | 0.917 | 6 | 1.589 |
| overlapping_phase_dependencies | theta_0173 | 8 | frozen | success | (176, 111, 7) | 0.8635 | 12 | 10.183 |
| overlapping_phase_dependencies | theta_0173 | 8 | static_ancilla | success | (190, 73, 7) | 0.917 | 2 | 15.114 |
| overlapping_phase_dependencies | theta_0173 | 8 | static_balanced | success | (176, 157, 7) | 0.875 | 3 | 2.654 |
| overlapping_phase_dependencies | theta_0173 | 8 | static_depth | success | (190, 73, 7) | 0.917 | 1 | 15.098 |
| overlapping_phase_dependencies | theta_0173 | 8 | static_t | success | (190, 73, 7) | 0.917 | 3 | 1.482 |
| qedc_small_phase_block | theta_0173 | 8 | adaptive | success | (228, 116, 4) | 1.08 | 6 | 60.205 |
| qedc_small_phase_block | theta_0173 | 8 | fixed_count_depth | success | (216, 210, 4) | 1.0494999999999999 | 6 | 6.013 |
| qedc_small_phase_block | theta_0173 | 8 | fixed_depth_count | success | (228, 116, 4) | 1.08 | 6 | 3.550 |
| qedc_small_phase_block | theta_0173 | 8 | frozen | success | (228, 116, 4) | 1.08 | 12 | 26.720 |
| qedc_small_phase_block | theta_0173 | 8 | static_ancilla | success | (228, 116, 4) | 1.08 | 2 | 15.242 |
| qedc_small_phase_block | theta_0173 | 8 | static_balanced | success | (216, 210, 4) | 1.0494999999999999 | 3 | 4.898 |
| qedc_small_phase_block | theta_0173 | 8 | static_depth | success | (228, 116, 4) | 1.08 | 1 | 15.276 |
| qedc_small_phase_block | theta_0173 | 8 | static_t | success | (228, 116, 4) | 1.08 | 3 | 11.434 |
| weighted_no_collective_group | theta_0173 | 8 | adaptive | success | (254, 252, 0) | 1.206 | 12 | 23.778 |
| weighted_no_collective_group | theta_0173 | 8 | fixed_count_depth | success | (254, 252, 0) | 1.206 | 1 | 1.000 |
| weighted_no_collective_group | theta_0173 | 8 | fixed_depth_count | success | (254, 254, 0) | 1.2065000000000001 | 0 | 0.049 |
| weighted_no_collective_group | theta_0173 | 8 | frozen | success | (254, 252, 0) | 1.206 | 12 | 23.381 |
| weighted_no_collective_group | theta_0173 | 8 | static_ancilla | success | (254, 254, 0) | 1.2065000000000001 | 3 | 15.055 |
| weighted_no_collective_group | theta_0173 | 8 | static_balanced | success | (254, 252, 0) | 1.206 | 3 | 4.542 |
| weighted_no_collective_group | theta_0173 | 8 | static_depth | success | (254, 254, 0) | 1.2065000000000001 | 2 | 15.061 |
| weighted_no_collective_group | theta_0173 | 8 | static_t | success | (254, 252, 0) | 1.206 | 3 | 3.994 |

Adaptive versus the combined static-preference portfolio: 2 wins, 1 ties, 2 regressions on 5 matched cases. Versus the fixed successive-sequence portfolio: 2 wins, 2 ties, 1 regressions on 5 cases. Versus frozen priorities: 0 wins, 5 ties, 0 regressions on 5 cases. Static and fixed portfolios split the same total call budget; each policy sees the same roots and actions.

## Portfolio Cost

Shared root preparation is counted once per portfolio; search wall time includes backend, verification, scheduling, and controller work.

| Case | Angle | Workspace budget | Portfolio | Calls | Wall seconds | Best J |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| exact_ccz_phase_diagnostic | theta_exact | 8 | adaptive | 12 | 1.989 | 0.0325 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | frozen | 12 | 1.727 | 0.0325 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | static combined | 12 | 0.570 | 0.03225 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | fixed combined | 12 | 0.927 | 0.0325 |
| qedc_small_phase_block | theta_0173 | 8 | adaptive | 6 | 60.205 | 1.08 |
| qedc_small_phase_block | theta_0173 | 8 | frozen | 12 | 26.720 | 1.08 |
| qedc_small_phase_block | theta_0173 | 8 | static combined | 9 | 46.576 | 1.0494999999999999 |
| qedc_small_phase_block | theta_0173 | 8 | fixed combined | 12 | 9.471 | 1.0494999999999999 |
| weighted_no_collective_group | theta_0173 | 8 | adaptive | 12 | 23.778 | 1.206 |
| weighted_no_collective_group | theta_0173 | 8 | frozen | 12 | 23.381 | 1.206 |
| weighted_no_collective_group | theta_0173 | 8 | static combined | 11 | 38.510 | 1.206 |
| weighted_no_collective_group | theta_0173 | 8 | fixed combined | 1 | 1.002 | 1.206 |
| overlapping_phase_dependencies | theta_0173 | 8 | adaptive | 12 | 10.098 | 0.8635 |
| overlapping_phase_dependencies | theta_0173 | 8 | frozen | 12 | 10.183 | 0.8635 |
| overlapping_phase_dependencies | theta_0173 | 8 | static combined | 9 | 34.123 | 0.875 |
| overlapping_phase_dependencies | theta_0173 | 8 | fixed combined | 12 | 4.871 | 0.875 |
| hwp_joint_optimization_witness | theta_0173 | 8 | adaptive | 12 | 10.587 | 0.86375 |
| hwp_joint_optimization_witness | theta_0173 | 8 | frozen | 12 | 8.678 | 0.86375 |
| hwp_joint_optimization_witness | theta_0173 | 8 | static combined | 9 | 33.990 | 0.8642500000000001 |
| hwp_joint_optimization_witness | theta_0173 | 8 | fixed combined | 12 | 4.601 | 0.8642500000000001 |
## Paired Optimization

Accepted steps on each selected circuit's parent chain.

| Case | Workspace budget | Policy | Backend action | Before | After |
| --- | ---: | --- | --- | --- | --- |
| exact_ccz_phase_diagnostic (theta_exact) | 8 | adaptive | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 8 | fixed_count_depth | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 8 | frozen | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 8 | static_ancilla | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 8 | static_balanced | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 8 | static_depth | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 8 | static_t | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| hwp_joint_optimization_witness (theta_0173) | 8 | adaptive | pyzx:zx_extract | (190, 73, 7) | (176, 114, 7) |
| hwp_joint_optimization_witness (theta_0173) | 8 | adaptive | pyzx:zx_extract | (176, 114, 7) | (176, 162, 7) |
| hwp_joint_optimization_witness (theta_0173) | 8 | adaptive | pyzx:zx_extract | (176, 162, 7) | (176, 112, 7) |
| hwp_joint_optimization_witness (theta_0173) | 8 | fixed_count_depth | pyzx:zx_extract | (190, 73, 7) | (176, 114, 7) |
| hwp_joint_optimization_witness (theta_0173) | 8 | frozen | pyzx:zx_extract | (190, 73, 7) | (176, 114, 7) |
| hwp_joint_optimization_witness (theta_0173) | 8 | frozen | pyzx:zx_extract | (176, 114, 7) | (176, 162, 7) |
| hwp_joint_optimization_witness (theta_0173) | 8 | frozen | pyzx:zx_extract | (176, 162, 7) | (176, 112, 7) |
| hwp_joint_optimization_witness (theta_0173) | 8 | static_balanced | pyzx:zx_extract | (190, 73, 7) | (176, 114, 7) |
| overlapping_phase_dependencies (theta_0173) | 8 | adaptive | pyzx:zx_extract | (190, 73, 7) | (176, 157, 7) |
| overlapping_phase_dependencies (theta_0173) | 8 | adaptive | pyzx:zx_extract | (176, 157, 7) | (176, 111, 7) |
| overlapping_phase_dependencies (theta_0173) | 8 | fixed_count_depth | pyzx:zx_extract | (190, 73, 7) | (176, 157, 7) |
| overlapping_phase_dependencies (theta_0173) | 8 | frozen | pyzx:zx_extract | (190, 73, 7) | (176, 157, 7) |
| overlapping_phase_dependencies (theta_0173) | 8 | frozen | pyzx:zx_extract | (176, 157, 7) | (176, 111, 7) |
| overlapping_phase_dependencies (theta_0173) | 8 | static_balanced | pyzx:zx_extract | (190, 73, 7) | (176, 157, 7) |
| qedc_small_phase_block (theta_0173) | 8 | fixed_count_depth | pyzx:zx_extract | (228, 116, 4) | (216, 210, 4) |
| qedc_small_phase_block (theta_0173) | 8 | static_balanced | pyzx:zx_extract | (228, 116, 4) | (216, 210, 4) |
| weighted_no_collective_group (theta_0173) | 8 | adaptive | pyzx:todd | (254, 254, 0) | (254, 254, 0) |
| weighted_no_collective_group (theta_0173) | 8 | adaptive | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group (theta_0173) | 8 | fixed_count_depth | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group (theta_0173) | 8 | frozen | pyzx:todd | (254, 254, 0) | (254, 254, 0) |
| weighted_no_collective_group (theta_0173) | 8 | frozen | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group (theta_0173) | 8 | static_balanced | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |
| weighted_no_collective_group (theta_0173) | 8 | static_t | pyzx:zx_extract | (254, 254, 0) | (254, 252, 0) |

## Decision Trace

Attempt log for one adaptive case, recorded when each decision occurred. `P` lists current count/depth/ancilla pressure plus objective weights.

Case: `exact_ccz_phase_diagnostic`, workspace budget: `8`.

| Step | Parent | Region | Action | Scratch | P | Priority and reason | T | D | A | J | Seconds | Status |
| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9525: count priority 0.900; 0 current events have T-slack | 7 -> 7 | 5 -> 4 | 0 -> 0 | 0.03275 -> 0.0325 | 0.028 | accepted |
| 2 | shared_parity:normalized_greedy_anchor_walk | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9525: count priority 0.900; 0 current events have T-slack; no_change_or_cycle | 7 -> 7 | 6 -> 4 | 0 -> 0 | 0.033 -> 0.0325 | 0.028 | no_change_or_cycle |
| 3 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9475: count priority 0.900; 1 current events have T-slack | 7 -> 7 | 4 -> 4 | 0 -> 0 | 0.0325 -> 0.0325 | 0.030 | accepted |
| 4 | hwp_adder_unitary:adder_compressor_unitary_cap_3 | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9502: count priority 0.900; 17 current events have T-slack | 45 -> 21 | 27 -> 17 | 4 -> 4 | 0.23425 -> 0.12375 | 0.204 | accepted |
| 5 | hwp_adder_unitary:adder_compressor_unitary_cap_2 | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9495: count priority 0.900; 16 current events have T-slack | 46 -> 20 | 28 -> 15 | 3 -> 3 | 0.23275 -> 0.1125 | 0.186 | accepted |
| 6 | hwp_adder_unitary:adder_compressor_unitary_cap_3\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9475: count priority 0.900; 48 current events have T-slack | 21 -> 21 | 17 -> 16 | 4 -> 4 | 0.12375 -> 0.1235 | 0.228 | accepted |
| 7 | hwp_adder_unitary:adder_compressor_unitary_cap_3\|pyzx:zx_extract\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9508: count priority 0.900; 27 current events have T-slack | 21 -> 21 | 16 -> 15 | 4 -> 4 | 0.1235 -> 0.12325 | 0.270 | accepted |
| 8 | independent:normalized_independent | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9475: count priority 0.900; 1 current events have T-slack; no_change_or_cycle | 7 -> 7 | 5 -> 4 | 0 -> 0 | 0.03275 -> 0.0325 | 0.030 | no_change_or_cycle |
| 9 | hwp_adder_unitary:adder_compressor_unitary_cap_2\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9473: count priority 0.900; 20 current events have T-slack | 20 -> 20 | 15 -> 13 | 3 -> 3 | 0.1125 -> 0.112 | 0.190 | accepted |
| 10 | hwp_adder_unitary:adder_compressor_unitary_cap_2\|pyzx:zx_extract\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9490: count priority 0.900; 21 current events have T-slack | 20 -> 20 | 13 -> 15 | 3 -> 3 | 0.112 -> 0.1125 | 0.244 | accepted |
| 11 | hwp_adder_unitary:adder_compressor_unitary_cap_4 | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.125) | 0.9465: count priority 0.900; 38 current events have T-slack | 58 -> 26 | 32 -> 14 | 7 -> 7 | 0.31275 -> 0.16425 | 0.322 | accepted |
| 12 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (0.9, 0.05, 0.05) | 0.9425: count priority 0.900; 3 current events have T-slack | 7 -> 7 | 4 -> 4 | 0 -> 0 | 0.0325 -> 0.0325 | 0.038 | accepted |

## Final Pareto Points

Each policy row's checksummed circuit artifact contains emitted gates and a replayable proof chain for every listed alternative.

| Case | Angle | Workspace budget | T | D | A | Implementations |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| exact_ccz_phase_diagnostic | theta_exact | 8 | 7 | 1 | 4 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_4 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | 7 | 2 | 2 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_2, hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract\|phase_ancilla:parallel_phase:region_0_17:scratch_2 |
| exact_ccz_phase_diagnostic | theta_exact | 8 | 7 | 3 | 0 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:tpar |
| hwp_joint_optimization_witness | theta_0173 | 8 | 176 | 112 | 7 | hwp_adder_unitary:adder_compressor_unitary_cap_4\|pyzx:zx_extract\|pyzx:zx_extract\|pyzx:zx_extract |
| hwp_joint_optimization_witness | theta_0173 | 8 | 190 | 73 | 7 | hwp_adder_unitary:adder_compressor_unitary_cap_4 |
| hwp_joint_optimization_witness | theta_0173 | 8 | 200 | 50 | 0 | independent:normalized_independent, independent:normalized_independent\|pyzx:zx_extract |
| overlapping_phase_dependencies | theta_0173 | 8 | 176 | 111 | 7 | hwp_adder_unitary:adder_compressor_unitary_cap_4\|pyzx:zx_extract\|pyzx:zx_extract |
| overlapping_phase_dependencies | theta_0173 | 8 | 190 | 73 | 7 | hwp_adder_unitary:adder_compressor_unitary_cap_4 |
| overlapping_phase_dependencies | theta_0173 | 8 | 200 | 150 | 0 | independent:normalized_independent\|pyzx:zx_extract, shared_parity:normalized_greedy_anchor_walk\|pyzx:zx_extract |
| overlapping_phase_dependencies | theta_0173 | 8 | 220 | 114 | 4 | hwp_adder_unitary:adder_compressor_unitary_cap_2\|phase_ancilla:parallel_phase:region_268_277:scratch_1\|pyzx:zx_extract, hwp_adder_unitary:adder_compressor_unitary_cap_2\|phase_ancilla:parallel_phase:region_292_301:scratch_1\|pyzx:zx_extract |
| overlapping_phase_dependencies | theta_0173 | 8 | 220 | 116 | 3 | hwp_adder_unitary:adder_compressor_unitary_cap_2\|feynman:phasefold |
| qedc_small_phase_block | theta_0173 | 8 | 216 | 210 | 4 | hwp_adder_unitary:adder_compressor_unitary_cap_3\|pyzx:zx_extract |
| qedc_small_phase_block | theta_0173 | 8 | 228 | 116 | 4 | hwp_adder_unitary:adder_compressor_unitary_cap_3 |
| qedc_small_phase_block | theta_0173 | 8 | 312 | 156 | 0 | independent:normalized_independent\|pyzx:zx_extract\|pyzx:todd\|pyzx:todd |
| weighted_no_collective_group | theta_0173 | 8 | 254 | 252 | 0 | independent:normalized_independent\|pyzx:todd\|pyzx:zx_extract, independent:normalized_independent\|pyzx:todd\|pyzx:zx_extract\|pyzx:zx_extract, independent:normalized_independent\|pyzx:zx_extract |

## Mechanism Conclusion

Ancilla-for-depth action observed: yes. Verified successive transformations observed: yes. Adaptive beats the matched static portfolio in 2/5 and the matched fixed-sequence portfolio in 2/5 cases. Versus frozen priorities: 0 wins, 5 ties, 0 regressions. A workspace-release/reuse mechanism has not been established.

Post-optimization T is reported only as a total because optimized gates no longer have a reliable arithmetic-versus-rotation attribution.

Recorded statuses: `success`=40.
