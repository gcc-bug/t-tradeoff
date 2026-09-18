<!-- Source: reports/single-demonstration.md; verbatim report body follows. Not rerun during initialization. -->

# Single Tradeoff Demonstration

Run date: `2026-09-16`. Code: `bd7627c6713f26bfa03ebc1e6bea507ff39d1cc1+dirty:6dab3fe6b7dc`. 
Input: `qedc_mc_006_003_000` (`sha256:86255510d024b5d5c25e5bfe6f291dac15a1ad5586dbee3495a396c08f6216e6`), angle 
`0.173`, total error `0.0001`. This is an 
existing development case, not held-out evidence.

## Frozen target

The predeclared zero-ancilla references fixed `D0 = 255` before 
custom discovery, giving `T-depth <= floor(1.10 * D0) = 280`. 
The objective is minimum T-count subject to that depth cap, at most eight 
additional clean qubits, and operator-norm approximation error at most `1e-4`. 
Ties use T-depth and then ancillas.

## Reference outcomes

| Strategy | Status | Best `(T,D_T,A)` | Attempts | Uncached calls | Time (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| raw_seed | success | (354, 174, 4) | 0 | 0 | 0.019 |
| repeated_pyzx | success | (336, 173, 4) | 18 | 17 | 68.140 |
| feynman_fixed_order | unavailable | unavailable | 0 | 0 | 0.000 |
| count_then_depth | success | (336, 171, 6) | 17 | 4 | 42.197 |
| depth_then_count | success | (336, 278, 8) | 16 | 5 | 33.014 |

The Feynman row requires a real executable. None was present, so no stub or 
estimate is reported. Every strategy otherwise started from the same complete 
independent/shared-parity/HWP seed catalog.

## Discovery and winner

Discovery stopped by `attempt_budget` after 120 unique attempts and 727.212 seconds. It retained only intermediate states satisfying the hard limits. For each state it considered 
at most one critical and one slack phase region, ranked by scheduled critical 
T participation and mean T-slack.

The complete run took 907.436 seconds, including 1.460 seconds of root preparation. Attempt statuses across references, discovery, and counterfactuals were: `accepted=126, backend_failure=11, hard_limit=8, hard_limit_precheck=30, not_applicable=4`.

| Step | Target | Action | Before | After | Verification | Scratch |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 1 | whole_circuit None | pyzx:zx_extract | (354, 174, 4) | (336, 173, 4) | verified_lowered_external_dense | alloc=[], reuse=[], release=[] |
| 2 | critical [962, 970] | phase_ancilla:parallel_phase | (336, 173, 4) | (336, 172, 5) | verified_lowered_external_dense | alloc=[10], reuse=[], release=[10] |
| 3 | critical [962, 980] | phase_ancilla:parallel_phase | (336, 172, 5) | (336, 171, 6) | verified_lowered_external_dense | alloc=[11], reuse=[10], release=[10, 11] |

The emitted winner is `hwp_adder_unitary:adder_compressor_unitary_auto_cap_3|pyzx:zx_extract|phase_ancilla:parallel_phase:critical_962_970:scratch_1|phase_ancilla:parallel_phase:critical_962_980:scratch_2` with resources `(336, 171, 6)` and replay status `verified_lowered_external_dense`. The raw trace records backend failures, hard-limit exclusions, verification, timing, cache status, and scratch IDs.

## Counterfactuals

| Sequence | Status | Endpoint `(T,D_T,A)` | Attempts |
| --- | --- | ---: | ---: |
| workspace_direct | success | (354, 173, 6) | 1 |
| reverse_depth_then_count | success | (336, 278, 8) | 2 |
| repeat_count_backend | success | (336, 173, 4) | 3 |
| alternate_count_then_cleanup | success | (342, 263, 4) | 2 |

Direct workspace resynthesis changes depth but not count. Reversing the two 
actions reaches the same T-count with substantially worse depth. Repeating the 
count backend makes no further count improvement after its first useful pass; 
the strategy retains that best prefix. Applying the same final cleanup after 
`full_optimize` does not improve the winner.

## Conclusion

A predeclared fixed count-then-depth sequence matches the discovered winner. The gain is one PyZX count simplification followed by selection of the current critical local phase region with two useful clean scratch wires. Updating a preference vector is not needed to obtain this result, so no new policy rule or adaptive-quality claim is added. The discovered chain exercises certified scratch reuse, but the fixed sequence allocates both wires at once and reaches the same endpoint, so reuse is not an enabling benefit here.

The local phase action is a limited clean-scratch CNOT/diagonal resynthesis, 
not a full T-par implementation. Whole-circuit PyZX invalidates scratch-pool 
metadata. The search does not cross an intermediate hard-limit violation, and 
dirty ancillas, measured cleanup, catalysts, and physical factory costs remain 
outside this experiment.

Reproduce with:

```bash
.venv/bin/python scripts/inspect_tradeoff_sequences.py --config configs/single-demonstration.yaml
```
