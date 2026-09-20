# Guided HWP search results

13 inputs × 27 queries × five methods × 3 timing repetitions. All optima and intervals were checked against the exact frontier. Preferences and extra inputs were frozen in the first commit. No construction was added.

## Matched query sequence

Times below sum per-query medians. Search/selection time includes incumbent emission and verification. Warm sequence totals charge one library build, model setup, and acquisition per input. The frontier is charged once across all 27 queries, not once per query. Archive acquisition includes six development queries for each of three exact limit fingerprints. Development targets use no archived certificates; only the nine hold-out queries per input receive them.

| Method | Query seconds | Acquisition seconds | Warm sequence seconds | Expanded states | Generated waves |
|---|---:|---:|---:|---:|---:|
| frontier | 1.1884 | 1.0490 | 3.3491 | 419 | 124423 |
| direct_trivial | 12.9007 | 0.0069 | 14.0193 | 12766 | 1568875 |
| reference_trivial | 12.8304 | 1.8480 | 15.7901 | 12736 | 1568778 |
| structural | 8.8917 | 1.8480 | 11.8513 | 928 | 804832 |
| archive | 8.8418 | 7.6356 | 17.5891 | 928 | 804832 |

## Cold and warm library costs

Measured process import/setup startup: 0.2601 s. Each cold library uses an empty synthesis cache; each warm figure is the median of three rebuilds with that case's rotation cache. A cold single query costs startup + cold library + model setup + its method acquisition + query time. A warm query with an already available library/archive costs the query time; the archive is never free in the sequence totals.

| Input | Options / templates | New rotations | Cold library s | Warm library s | Frontier s | Reference acquisition s |
|---|---:|---:|---:|---:|---:|---:|
| native_3 | 11 / 5 | 4 | 1.0344 | 0.0064 | 0.0001 | 0.0098 |
| native_4 | 26 / 7 | 7 | 0.2730 | 0.0130 | 0.0003 | 0.0175 |
| native_5 | 57 / 9 | 10 | 0.4085 | 0.0275 | 0.0012 | 0.0242 |
| native_6 | 120 / 11 | 13 | 0.5920 | 0.0554 | 0.0082 | 0.0537 |
| native_8 | 502 / 15 | 17 | 0.9469 | 0.2742 | 0.9630 | 1.2968 |
| heterogeneous_3_2 | 15 / 8 | 6 | 0.2307 | 0.0103 | 0.0004 | 0.0234 |
| overlapping_6 | 67 / 53 | 13 | 0.6259 | 0.0802 | 0.0011 | 0.0312 |
| qedc_mc_004_003_000 | 63 / 46 | 13 | 0.5482 | 0.0743 | 0.0008 | 0.0291 |
| distinct_angles_4 | 4 / 4 | 4 | 0.1408 | 0.0022 | 0.0001 | 0.0183 |
| native_2_holdout | 4 / 3 | 2 | 0.0720 | 0.0027 | 0.0000 | 0.0083 |
| native_7_holdout | 247 / 13 | 16 | 0.7313 | 0.1173 | 0.0713 | 0.2570 |
| groups_2_2_2_holdout | 12 / 9 | 6 | 0.2445 | 0.0087 | 0.0011 | 0.0488 |
| overlap_seed_holdout | 63 / 56 | 13 | 0.6589 | 0.0886 | 0.0014 | 0.0299 |

## Bound transfer on held-out weights

| Input | Structural states | Archive states | Structural query s | Archive query s | Archive acquisition s |
|---|---:|---:|---:|---:|---:|
| native_3 | 6 | 6 | 0.0157 | 0.0162 | 0.0336 |
| native_4 | 6 | 6 | 0.0217 | 0.0226 | 0.0502 |
| native_5 | 6 | 6 | 0.0344 | 0.0329 | 0.0560 |
| native_6 | 6 | 6 | 0.0702 | 0.0713 | 0.1224 |
| native_8 | 6 | 6 | 2.6457 | 2.6236 | 4.5547 |
| heterogeneous_3_2 | 6 | 6 | 0.0295 | 0.0309 | 0.0627 |
| overlapping_6 | 99 | 99 | 0.0443 | 0.0433 | 0.1067 |
| qedc_mc_004_003_000 | 62 | 62 | 0.0422 | 0.0419 | 0.0852 |
| distinct_angles_4 | 0 | 0 | 0.0212 | 0.0225 | 0.0418 |
| native_2_holdout | 0 | 0 | 0.0100 | 0.0108 | 0.0243 |
| native_7_holdout | 6 | 6 | 0.2919 | 0.2861 | 0.4778 |
| groups_2_2_2_holdout | 0 | 0 | 0.0401 | 0.0391 | 0.0830 |
| overlap_seed_holdout | 139 | 139 | 0.0444 | 0.0448 | 0.0894 |

## Guarantees and evidence

Final method/query statuses: {'OPTIMAL': 1755}.

The machine-readable results include every preference and exact effective coefficient, limits, model fingerprint, reconstructed plan, measured emitted resources, U/L, absolute/relative gaps, three individual timings, states/waves, time to first improved incumbent, and times to 5%/1% certified gaps. Null threshold times mean the threshold was not reached; L=0 has no relative percentage. Options/templates and new rotations are reported separately. Library time includes template verification; query verification is also recorded separately.

The tracked witness emits the constrained overlapping_6 circuit with modeled (T, wave D, A) = (284,166,3). Its JSON includes the original program, candidate, Clifford+T lowering, ordinary scheduled resources, verification evidence, and exact cost interval. The midpoint argument excludes using this witness as an unrestricted linear-cost win. The frozen baseline diagnosis found no unrestricted wins and two constrained cost wins among 351 queries; H2 remains unestablished.

All five methods use identical templates, objective scales, legal waves and verification; seeds, structural bounds and archived inequalities are the intentionally varied components. The three search repetitions have the same 10-second deadline. Exact-frontier/reference acquisition retains its separately declared 120/180-second caps; all completed. No certificates come from the full frontier. Single-certificate transfer uses exact rational feasibility checks. No downstream optimizer was run, so there is no post-optimization guarantee.

These tiny-case timings do not establish broad speedups. Compare work counts and charged totals, not isolated sub-millisecond differences. The complete library is synthesized up front in every method; this experiment cannot claim avoided subset synthesis. See the accompanying assessment in docs/hwp-guided-search.md for the stopping decision.
