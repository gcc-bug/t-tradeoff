# Adaptive Resource Tradeoff Study

Results: `results/raw/ancilla-depth-diagnostic`

Code revision: `4d84d70ba17f012dd4c0023701073dd9213de1d1+dirty:875d5cf92434`. Config hash: `a3da47cbe80bd1ea8d026994c61d5ecc2e89f7e19696919bb99f9771969bfdc6`. Manifest hash: `1d7e804bcfcaf6a942599b1bc4e62dc99111db198a1813e3003d09421ff9acc8`.

Fixed final objective: `{"metric": "t_depth", "mode": "single"}`. Hard limits by workspace budget: `{"0": {"ancilla": 0, "t_count": 7, "t_depth": 5}, "4": {"ancilla": 4, "t_count": 7, "t_depth": 5}}`.

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
| exact_ccz_phase_diagnostic | theta_exact | 0 | adaptive | success | (7, 3, 0) | 3.0 | 12 | 0.476 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | fixed_count_depth | success | (7, 4, 0) | 4.0 | 2 | 0.074 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | fixed_depth_count | success | (7, 5, 0) | 5.0 | 0 | 0.008 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | frozen | success | (7, 3, 0) | 3.0 | 12 | 0.450 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_ancilla | success | (7, 3, 0) | 3.0 | 3 | 0.107 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_balanced | success | (7, 4, 0) | 4.0 | 3 | 0.117 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_depth | success | (7, 3, 0) | 3.0 | 3 | 0.121 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_t | success | (7, 4, 0) | 4.0 | 3 | 0.107 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | adaptive | success | (7, 1, 4) | 1.0 | 12 | 0.212 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | fixed_count_depth | success | (7, 1, 4) | 1.0 | 6 | 0.165 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | fixed_depth_count | success | (7, 1, 4) | 1.0 | 6 | 0.105 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | frozen | success | (7, 1, 4) | 1.0 | 12 | 0.287 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_ancilla | success | (7, 3, 0) | 3.0 | 3 | 0.115 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_balanced | success | (7, 4, 0) | 4.0 | 3 | 0.114 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_depth | success | (7, 3, 0) | 3.0 | 3 | 0.094 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_t | success | (7, 4, 0) | 4.0 | 3 | 0.123 |

Adaptive versus the combined static-preference portfolio: 1 wins, 1 ties, 0 regressions on 2 matched cases. Versus the fixed successive-sequence portfolio: 1 wins, 1 ties, 0 regressions on 2 cases. Versus frozen priorities: 0 wins, 2 ties, 0 regressions on 2 cases. Static and fixed portfolios split the same total call budget; each policy sees the same roots and actions.

## Portfolio Cost

Shared root preparation is counted once per portfolio; search wall time includes backend, verification, scheduling, and controller work.

| Case | Angle | Workspace budget | Portfolio | Calls | Wall seconds | Best J |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| exact_ccz_phase_diagnostic | theta_exact | 4 | adaptive | 12 | 0.212 | 1.0 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | frozen | 12 | 0.287 | 1.0 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static combined | 12 | 0.406 | 3.0 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | fixed combined | 12 | 0.257 | 1.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | adaptive | 12 | 0.476 | 3.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | frozen | 12 | 0.450 | 3.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static combined | 12 | 0.429 | 3.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | fixed combined | 2 | 0.074 | 4.0 |
## Paired Optimization

Accepted steps on each selected circuit's parent chain.

| Case | Workspace budget | Policy | Backend action | Before | After |
| --- | ---: | --- | --- | --- | --- |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | adaptive | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | fixed_count_depth | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | frozen | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_ancilla | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_balanced | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_depth | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_t | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | adaptive | phase_ancilla:parallel_phase | (7, 5, 0) | (7, 1, 4) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | fixed_count_depth | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | fixed_count_depth | phase_ancilla:parallel_phase | (7, 4, 0) | (7, 1, 4) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | fixed_depth_count | phase_ancilla:parallel_phase | (7, 5, 0) | (7, 1, 4) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | frozen | phase_ancilla:parallel_phase | (7, 5, 0) | (7, 1, 4) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_ancilla | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_balanced | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_depth | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_t | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |

## Decision Trace

Attempt log for one adaptive case, recorded when each decision occurred. `P` lists current count/depth/ancilla pressure plus objective weights.

Case: `exact_ccz_phase_diagnostic`, workspace budget: `4`.

| Step | Parent | Region | Action | Scratch | P | Priority and reason | T | D | A | J | Seconds | Status |
| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | whole_circuit | feynman:tpar | 0 | (0.2, 1.2, 0.0) | 1.8800: 7/7 T gates are on a critical dependency path; prioritize depth resynthesis | 7 -> 7 | 5 -> 3 | 0 -> 0 | 5 -> 3 | 0.032 | accepted |
| 2 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | 0:17 | phase_ancilla:parallel_phase | 1 | (0.2, 1.2, 0.0) | 1.8000: 7/7 T gates on critical paths; 1 clean scratch wires requested for a supported CNOT/phase region; depth gain is unproven | 7 -> 7 | 5 -> 4 | 0 -> 1 | 5 -> 4 | 0.009 | accepted |
| 3 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_1 | whole_circuit | feynman:tpar | 0 | (0.2, 1.0, 0.0) | 1.5800: 7/7 T gates are on a critical dependency path; prioritize depth resynthesis; feynopt: Can't reify False + q1 = 0 | 7 -> 7 | 4 -> 4 | 1 -> 1 | 4 -> 4 | 0.011 | backend_failure |
| 4 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | 0:17 | phase_ancilla:parallel_phase | 2 | (0.2, 1.2, 0.0) | 1.8000: 7/7 T gates on critical paths; 2 clean scratch wires requested for a supported CNOT/phase region; depth gain is unproven | 7 -> 7 | 5 -> 2 | 0 -> 2 | 5 -> 2 | 0.007 | accepted |
| 5 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | 0:17 | phase_ancilla:parallel_phase | 4 | (0.2, 1.2, 0.0) | 1.8000: 7/7 T gates on critical paths; 4 clean scratch wires requested for a supported CNOT/phase region; depth gain is unproven | 7 -> 7 | 5 -> 1 | 0 -> 4 | 5 -> 1 | 0.005 | accepted |
| 6 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_2 | whole_circuit | feynman:tpar | 0 | (0.2, 1.0, 0.0) | 1.5800: 7/7 T gates are on a critical dependency path; prioritize depth resynthesis; feynopt: Can't reify False + q1 = 0 | 7 -> 7 | 2 -> 2 | 2 -> 2 | 2 -> 2 | 0.012 | backend_failure |
| 7 | independent:normalized_independent | whole_circuit | feynman:tpar | 0 | (0.2, 1.2, 0.0) | 1.7086: 6/7 T gates are on a critical dependency path; prioritize depth resynthesis; no_change_or_cycle | 7 -> 7 | 5 -> 3 | 0 -> 0 | 5 -> 3 | 0.033 | no_change_or_cycle |
| 8 | independent:normalized_independent | 0:17 | phase_ancilla:parallel_phase | 1 | (0.2, 1.2, 0.0) | 1.6286: 6/7 T gates on critical paths; 1 clean scratch wires requested for a supported CNOT/phase region; depth gain is unproven | 7 -> 7 | 5 -> 4 | 0 -> 1 | 5 -> 4 | 0.007 | accepted |
| 9 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_4 | whole_circuit | feynman:tpar | 0 | (0.2, 1.0, 0.2) | 1.5800: 7/7 T gates are on a critical dependency path; prioritize depth resynthesis; feynopt: Can't reify False + q1 = 0 | 7 -> 7 | 1 -> 1 | 4 -> 4 | 1 -> 1 | 0.009 | backend_failure |
| 10 | independent:normalized_independent | 0:17 | phase_ancilla:parallel_phase | 2 | (0.2, 1.2, 0.0) | 1.6286: 6/7 T gates on critical paths; 2 clean scratch wires requested for a supported CNOT/phase region; depth gain is unproven | 7 -> 7 | 5 -> 2 | 0 -> 2 | 5 -> 2 | 0.007 | accepted |
| 11 | independent:normalized_independent | 0:17 | phase_ancilla:parallel_phase | 4 | (0.2, 1.2, 0.0) | 1.6286: 6/7 T gates on critical paths; 4 clean scratch wires requested for a supported CNOT/phase region; depth gain is unproven | 7 -> 7 | 5 -> 1 | 0 -> 4 | 5 -> 1 | 0.008 | accepted |
| 12 | independent:normalized_independent\|phase_ancilla:parallel_phase:region_0_17:scratch_2 | whole_circuit | feynman:tpar | 0 | (0.2, 1.0, 0.0) | 1.5800: 7/7 T gates are on a critical dependency path; prioritize depth resynthesis | 7 -> 7 | 2 -> 2 | 2 -> 2 | 2 -> 2 | 0.048 | accepted |

## Final Pareto Points

Each policy row's checksummed circuit artifact contains emitted gates and a replayable proof chain for every listed alternative.

| Case | Angle | Workspace budget | T | D | A | Implementations |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| exact_ccz_phase_diagnostic | theta_exact | 0 | 7 | 3 | 0 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:tpar |
| exact_ccz_phase_diagnostic | theta_exact | 4 | 7 | 1 | 4 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_4, hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract\|phase_ancilla:parallel_phase:region_0_17:scratch_4, independent:normalized_independent\|phase_ancilla:parallel_phase:region_0_17:scratch_4 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | 7 | 2 | 1 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:tpar\|phase_ancilla:parallel_phase:region_0_18:scratch_1\|feynman:tpar |
| exact_ccz_phase_diagnostic | theta_exact | 4 | 7 | 3 | 0 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:tpar |

## Mechanism Conclusion

Ancilla-for-depth action observed: yes. Verified successive transformations observed: yes. Adaptive beats the matched static portfolio in 1/2 and the matched fixed-sequence portfolio in 1/2 cases. Versus frozen priorities: 0 wins, 2 ties, 0 regressions. A workspace-release/reuse mechanism has not been established.

Post-optimization T is reported only as a total because optimized gates no longer have a reliable arithmetic-versus-rotation attribution.

Recorded statuses: `success`=16.
