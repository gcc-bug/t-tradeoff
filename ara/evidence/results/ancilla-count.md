<!-- Source: reports/ancilla-count.md; verbatim report body follows. Not rerun during initialization. -->

# Adaptive Resource Tradeoff Study

Results: `results/raw/ancilla-count-diagnostic`

Code revision: `4d84d70ba17f012dd4c0023701073dd9213de1d1+dirty:875d5cf92434`. Config hash: `3c99483b7abaae1a0931b203087eaca5af8cd81ea4bf887e439c40c2c14f0e54`. Manifest hash: `1d7e804bcfcaf6a942599b1bc4e62dc99111db198a1813e3003d09421ff9acc8`.

Fixed final objective: `{"metric": "t_count", "mode": "single"}`. Hard limits by workspace budget: `{"0": {"ancilla": 0, "t_count": 7, "t_depth": 5}, "4": {"ancilla": 4, "t_count": 7, "t_depth": 5}}`.

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
| exact_ccz_phase_diagnostic | theta_exact | 0 | adaptive | success | (7, 4, 0) | 7.0 | 12 | 0.334 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | fixed_count_depth | success | (7, 4, 0) | 7.0 | 2 | 0.054 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | fixed_depth_count | success | (7, 5, 0) | 7.0 | 0 | 0.006 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | frozen | success | (7, 4, 0) | 7.0 | 12 | 0.328 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_ancilla | success | (7, 3, 0) | 7.0 | 3 | 0.078 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_balanced | success | (7, 4, 0) | 7.0 | 3 | 0.081 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_depth | success | (7, 3, 0) | 7.0 | 3 | 0.098 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static_t | success | (7, 4, 0) | 7.0 | 3 | 0.084 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | adaptive | success | (7, 4, 0) | 7.0 | 12 | 0.380 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | fixed_count_depth | success | (7, 1, 4) | 7.0 | 6 | 0.127 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | fixed_depth_count | success | (7, 1, 4) | 7.0 | 6 | 0.091 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | frozen | success | (7, 4, 0) | 7.0 | 12 | 0.333 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_ancilla | success | (7, 3, 0) | 7.0 | 3 | 0.087 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_balanced | success | (7, 4, 0) | 7.0 | 3 | 0.087 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_depth | success | (7, 3, 0) | 7.0 | 3 | 0.072 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static_t | success | (7, 4, 0) | 7.0 | 3 | 0.087 |

Adaptive versus the combined static-preference portfolio: 0 wins, 2 ties, 0 regressions on 2 matched cases. Versus the fixed successive-sequence portfolio: 0 wins, 2 ties, 0 regressions on 2 cases. Versus frozen priorities: 0 wins, 2 ties, 0 regressions on 2 cases. Static and fixed portfolios split the same total call budget; each policy sees the same roots and actions.

## Portfolio Cost

Shared root preparation is counted once per portfolio; search wall time includes backend, verification, scheduling, and controller work.

| Case | Angle | Workspace budget | Portfolio | Calls | Wall seconds | Best J |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| exact_ccz_phase_diagnostic | theta_exact | 4 | adaptive | 12 | 0.380 | 7.0 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | frozen | 12 | 0.333 | 7.0 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | static combined | 12 | 0.300 | 7.0 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | fixed combined | 12 | 0.207 | 7.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | adaptive | 12 | 0.334 | 7.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | frozen | 12 | 0.328 | 7.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | static combined | 12 | 0.325 | 7.0 |
| exact_ccz_phase_diagnostic | theta_exact | 0 | fixed combined | 2 | 0.054 | 7.0 |
## Paired Optimization

Accepted steps on each selected circuit's parent chain.

| Case | Workspace budget | Policy | Backend action | Before | After |
| --- | ---: | --- | --- | --- | --- |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | adaptive | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | fixed_count_depth | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | frozen | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_ancilla | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_balanced | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_depth | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 0 | static_t | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | adaptive | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | fixed_count_depth | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | fixed_count_depth | phase_ancilla:parallel_phase | (7, 4, 0) | (7, 1, 4) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | fixed_depth_count | phase_ancilla:parallel_phase | (7, 5, 0) | (7, 1, 4) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | frozen | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_ancilla | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_balanced | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_depth | feynman:tpar | (7, 5, 0) | (7, 3, 0) |
| exact_ccz_phase_diagnostic (theta_exact) | 4 | static_t | pyzx:zx_extract | (7, 5, 0) | (7, 4, 0) |

## Decision Trace

Attempt log for one adaptive case, recorded when each decision occurred. `P` lists current count/depth/ancilla pressure plus objective weights.

Case: `exact_ccz_phase_diagnostic`, workspace budget: `0`.

| Step | Parent | Region | Action | Scratch | P | Priority and reason | T | D | A | J | Seconds | Status |
| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | whole_circuit | pyzx:zx_extract | 0 | (1.2, 0.2, 0.0) | 1.4100: count priority 1.200; 0 current events have T-slack | 7 -> 7 | 5 -> 4 | 0 -> 0 | 7 -> 7 | 0.024 | accepted |
| 2 | independent:normalized_independent | whole_circuit | pyzx:zx_extract | 0 | (1.2, 0.2, 0.0) | 1.3900: count priority 1.200; 1 current events have T-slack; no_change_or_cycle | 7 -> 7 | 5 -> 4 | 0 -> 0 | 7 -> 7 | 0.023 | no_change_or_cycle |
| 3 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract | whole_circuit | pyzx:todd | 0 | (1.2, 0.0, 0.0) | 1.2000: count priority 1.200; 1 current events have T-slack; hard_limit | 7 -> 7 | 4 -> 6 | 0 -> 0 | 7 -> 7 | 0.031 | hard_limit |
| 4 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | whole_circuit | pyzx:todd | 0 | (1.2, 0.2, 0.0) | 1.3200: count priority 1.200; 0 current events have T-slack; hard_limit | 7 -> 7 | 5 -> 6 | 0 -> 0 | 7 -> 7 | 0.022 | hard_limit |
| 5 | independent:normalized_independent | whole_circuit | pyzx:todd | 0 | (1.2, 0.2, 0.0) | 1.3086: count priority 1.200; 1 current events have T-slack; hard_limit | 7 -> 7 | 5 -> 6 | 0 -> 0 | 7 -> 7 | 0.024 | hard_limit |
| 6 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (1.2, 0.0, 0.0) | 1.2000: count priority 1.200; 1 current events have T-slack | 7 -> 7 | 4 -> 4 | 0 -> 0 | 7 -> 7 | 0.027 | accepted |
| 7 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract\|pyzx:zx_extract | whole_circuit | pyzx:todd | 0 | (1.2, 0.0, 0.0) | 1.2000: count priority 1.200; 3 current events have T-slack; hard_limit | 7 -> 7 | 4 -> 6 | 0 -> 0 | 7 -> 7 | 0.035 | hard_limit |
| 8 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract\|pyzx:zx_extract | whole_circuit | pyzx:zx_extract | 0 | (1.2, 0.0, 0.0) | 1.2000: count priority 1.200; 3 current events have T-slack | 7 -> 7 | 4 -> 4 | 0 -> 0 | 7 -> 7 | 0.034 | accepted |
| 9 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract | whole_circuit | feynman:phasefold | 0 | (1.2, 0.0, 0.0) | 1.0800: count priority 1.200; 1 current events have T-slack; no_change_or_cycle | 7 -> 7 | 4 -> 4 | 0 -> 0 | 7 -> 7 | 0.028 | no_change_or_cycle |
| 10 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | whole_circuit | feynman:phasefold | 0 | (1.2, 0.2, 0.0) | 1.1400: count priority 1.200; 0 current events have T-slack | 7 -> 7 | 5 -> 5 | 0 -> 0 | 7 -> 7 | 0.023 | accepted |
| 11 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:phasefold | whole_circuit | pyzx:zx_extract | 0 | (1.2, 0.2, 0.0) | 1.4100: count priority 1.200; 0 current events have T-slack; no_change_or_cycle | 7 -> 7 | 5 -> 4 | 0 -> 0 | 7 -> 7 | 0.028 | no_change_or_cycle |
| 12 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:phasefold | whole_circuit | pyzx:todd | 0 | (1.2, 0.2, 0.0) | 1.3200: count priority 1.200; 0 current events have T-slack; hard_limit | 7 -> 7 | 5 -> 6 | 0 -> 0 | 7 -> 7 | 0.025 | hard_limit |

## Final Pareto Points

Each policy row's checksummed circuit artifact contains emitted gates and a replayable proof chain for every listed alternative.

| Case | Angle | Workspace budget | T | D | A | Implementations |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| exact_ccz_phase_diagnostic | theta_exact | 0 | 7 | 3 | 0 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:tpar |
| exact_ccz_phase_diagnostic | theta_exact | 4 | 7 | 1 | 4 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_4, hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract\|phase_ancilla:parallel_phase:region_0_17:scratch_4 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | 7 | 2 | 2 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|phase_ancilla:parallel_phase:region_0_17:scratch_2, hwp_adder_unitary:adder_compressor_unitary_cap_1\|pyzx:zx_extract\|phase_ancilla:parallel_phase:region_0_17:scratch_2 |
| exact_ccz_phase_diagnostic | theta_exact | 4 | 7 | 3 | 0 | hwp_adder_unitary:adder_compressor_unitary_cap_1\|feynman:tpar |

## Mechanism Conclusion

Ancilla-for-depth action observed: yes. Verified successive transformations observed: yes. Adaptive beats the matched static portfolio in 0/2 and the matched fixed-sequence portfolio in 0/2 cases. Versus frozen priorities: 0 wins, 2 ties, 0 regressions. A workspace-release/reuse mechanism has not been established.

Post-optimization T is reported only as a total because optimized gates no longer have a reliable arithmetic-versus-rotation attribution.

Recorded statuses: `success`=16.
