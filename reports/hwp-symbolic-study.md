# HWP symbolic bounds: frozen comparison

Costs certify only the enumerated unitary construction family, fixed normalized-term precision, and complete-wave depth. Ordinary emitted T-depth is recorded separately. All timings include setup, seed acquisition, failed search work, lowering, and verification. Three independent cache lifecycles are reported individually in the evidence.

| Space / mode | Method | Total median seconds across cases | Certified optimal / queried samples |
|---|---|---:|---:|
| expanded / cold | frontier | 45.5511 | 42 / 54 |
| expanded / cold | guided | 36.4255 | 40 / 54 |
| expanded / cold | symbolic | 12.0393 | 33 / 54 |
| expanded / cold | symbolic_resolved | 12.0586 | 33 / 54 |
| expanded / cold | symbolic_unpruned | 12.0601 | 33 / 54 |
| expanded / warm | frontier | 46.2298 | 978 / 1098 |
| expanded / warm | guided | 65.3412 | 1019 / 1098 |
| expanded / warm | symbolic | 40.8880 | 1004 / 1098 |
| expanded / warm | symbolic_resolved | 32.0354 | 1039 / 1098 |
| expanded / warm | symbolic_unpruned | 56.7591 | 960 / 1098 |
| original / cold | frontier | 30.7405 | 48 / 54 |
| original / cold | guided | 26.2392 | 45 / 54 |
| original / cold | symbolic | 11.5604 | 34 / 54 |
| original / cold | symbolic_resolved | 11.6656 | 38 / 54 |
| original / cold | symbolic_unpruned | 11.4480 | 35 / 54 |
| original / warm | frontier | 32.5417 | 1068 / 1098 |
| original / warm | guided | 39.5847 | 1069 / 1098 |
| original / warm | symbolic | 29.8930 | 1035 / 1098 |
| original / warm | symbolic_resolved | 24.3055 | 1058 / 1098 |
| original / warm | symbolic_unpruned | 43.1093 | 1011 / 1098 |

The table above includes interrupted queries; unequal completion rates are not equal-quality speedups.

| Original space, matched complete outcomes | Cases | Frontier median s | Symbolic median s |
|---|---:|---:|---:|
| cold | 11 | 5.0675 | 3.9041 |
| warm | 11 | 6.2534 | 6.5184 |

| Circuit quality under matched constraints | Verified strict wins over old certified optimum |
|---|---:|
| distinct_angles_4 | 0 |
| groups_2_2_2_holdout | 0 |
| groups_5_5 | 0 |
| heterogeneous_3_2 | 0 |
| native_10 | 0 |
| native_2_holdout | 0 |
| native_3 | 0 |
| native_4 | 0 |
| native_5 | 0 |
| native_6 | 1 |
| native_7_holdout | 2 |
| native_8 | 0 |
| native_9 | 0 |
| overlap_fresh_1 | 0 |
| overlap_fresh_2 | 0 |
| overlap_seed_holdout | 0 |
| overlapping_6 | 0 |
| qedc_mc_004_003_000 | 0 |

H2: 3 distinct case/query improvements are certified against the old-space bound, on native sizes six and seven. The improved single-wave resource tuple is `(204,68,4)`, versus the old optimum `(204,74,4)`: depth improves while T-count and workspace remain equal. The expanded uniform/per-group batching reference also finds this circuit. The native-six witness lowers its frozen objective from `93/130` to `183/260` (1.61%) and passes a separate dense check with operator-norm error `3.3788e-5`, below `1e-4`. Its complete recipe and circuit are in `results/hwp-symbolic-witness.json.gz`. A zero count does not establish that every larger arithmetic family is unhelpful.

H1 has a narrow positive result: on the 11 original-space inputs where both methods completed all matched queries in all repetitions, cold symbolic evaluation totals 3.9041 s versus 5.0675 s for the frontier (about 23% lower, summing per-case medians). The paired aggregate repetitions are frontier `[5.9095, 5.1735, 5.0304]` s and symbolic `[3.8026, 3.8646, 4.0745]` s. Warm totals are 6.5184 s versus 6.2534 s, with no repeatable symbolic advantage. The full declared workload has unequal certification rates, so it does not establish a general equal-quality speedup. The full-frontier baseline is charged once in warm sequences. Deadline overruns can include one atomic synthesis or verification call. DP interruptions retain feasible plans and use the safe lower bound zero; their incomplete frontier is never called an optimum.

The separate memory samples use tracemalloc: phase peaks are inclusive absolute Python heap high-water marks (nested work is included); timing phase buckets are exclusive. Native allocator memory inside numerical libraries is not covered. Memory runs are excluded from timing aggregates. Setup/search/other includes descriptor enumeration in the eager path and wave enumeration in both paths.

Strong uniform/per-group batching frontiers, including both arithmetic orderings, are measured separately with their own completion flags. An interrupted reference is not a certified optimum. No post-optimization or publication step was performed.

Cold denotes an empty synthesis cache within the same Python process. Interpreter startup and final serialization are excluded. Null in-loop gap timestamps do not override a final closed interval; final elapsed time is the available observation when closure occurs on queue exhaustion.
