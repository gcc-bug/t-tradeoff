# M2-R Rotation-Arithmetic Tradeoff Evaluation

Results: results/raw/tradeoff-pilot

The primary question in this development pilot is the structural tradeoff: how many arbitrary rotation syntheses are removed, and what reversible arithmetic, Clifford work, and clean workspace replace them. T-count and T-depth are reported as consequences under one matched lowering configuration, not as the research objective by themselves.

Legacy macros and unresolved catalytic or measurement-assisted estimates are excluded from primary evidence.

## Status

- success: 104

## Raw mechanism tradeoff

The comparison below uses the raw rule, not the objective-selected fallback. Deltas are `raw - independent`, so a negative rotation delta means that the rewrite removed rotation syntheses.

The rule fired in 6 of 13 cases and matched 11 disjoint triples. Across the active cases it exchanged 22 generic rotations for 22 logical Toffolis and 66 CNOTs. The three clean workspace qubits are reused across triples within a circuit.

| Stratum | Case | Triples | Delta generic rotations | Delta Toffolis | Delta CNOTs | Delta workspace | Delta T | Delta T-depth |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| negative_control | negative_irregular_masks | 0 | +0 | +0 | +0 | +0 | +0 | +0 |
| negative_control | negative_weighted_path | 0 | +0 | +0 | +0 | +0 | +0 | +0 |
| public | qedc_mc_004_003_000 | 1 | -2 | +2 | +6 | +3 | -98 | -52 |
| public | qedc_mc_006_003_000 | 2 | -4 | +4 | +12 | +3 | -186 | -90 |
| public | qedc_mc_008_003_000 | 2 | -4 | +4 | +12 | +3 | -180 | +16 |
| synthetic_diagnostic | diagnostic_biclique_3_4 | 0 | +0 | +0 | +0 | +0 | +0 | +0 |
| synthetic_diagnostic | diagnostic_clique_6 | 4 | -8 | +8 | +24 | +3 | -420 | -212 |
| synthetic_diagnostic | diagnostic_cycle_8 | 0 | +0 | +0 | +0 | +0 | +0 | +0 |
| synthetic_diagnostic | diagnostic_dependent | 1 | -2 | +2 | +6 | +3 | -86 | -42 |
| synthetic_diagnostic | diagnostic_duplicates | 0 | +0 | +0 | +0 | +0 | +0 | +0 |
| synthetic_diagnostic | diagnostic_path_8 | 0 | +0 | +0 | +0 | +0 | +0 | +0 |
| synthetic_diagnostic | diagnostic_star_8 | 0 | +0 | +0 | +0 | +0 | +0 | +0 |
| synthetic_diagnostic | diagnostic_triangle | 1 | -2 | +2 | +6 | +3 | -92 | -98 |

The aggregate observed signature per matched triple in this pilot is `-2` generic rotations, `+2` logical Toffolis, and `+6` CNOTs. The CNOT exchange depends on predicate supports and the parity network; it is not a universal constant of the identity.

T and T-depth deltas depend on angle, synthesis tolerance, parallelism, and the number of rotations sharing the total error budget; they are not the definition of the tradeoff.

## Absolute construction results

`Rotations` is shown as generic/exact application requests before gate decomposition. Toffoli and CNOT counts are logical emitted operations before Clifford+T lowering.

| Stratum | Case | Method | Status | Rotations | Toffoli | CNOT | Workspace | T | T-depth | Error bound | Verification | Evidence eligible |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| negative_control | negative_irregular_masks | dependent_triples_raw | success | 4/0 | 0 | 12 | 0 | 200 | 100 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | dependent_triples_selected | success | 4/0 | 0 | 12 | 0 | 200 | 100 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_dependency_simplified | success | 4/0 | 0 | 12 | 0 | 200 | 100 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_emitted | success | 4/0 | 0 | 12 | 0 | 200 | 100 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_emitted_triple_grouped | success | 4/0 | 0 | 12 | 0 | 200 | 100 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_macro_legacy | success | 4/0 | 0 | 12 | 0 | 200 | 100 | 4.245637346821135e-05 | verified_lowered_dense | no |
| negative_control | negative_irregular_masks | independent | success | 4/0 | 0 | 12 | 0 | 200 | 100 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | shared_parity | success | 4/0 | 0 | 12 | 0 | 200 | 150 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | dependent_triples_raw | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | dependent_triples_selected | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_dependency_simplified | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_emitted | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_emitted_triple_grouped | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_macro_legacy | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | no |
| negative_control | negative_weighted_path | independent | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | shared_parity | success | 5/0 | 0 | 10 | 0 | 254 | 254 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | dependent_triples_raw | success | 4/0 | 2 | 18 | 3 | 214 | 208 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | dependent_triples_selected | success | 4/0 | 2 | 18 | 3 | 214 | 208 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_dependency_simplified | success | 4/0 | 2 | 18 | 3 | 214 | 208 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_emitted | success | 4/0 | 12 | 36 | 5 | 284 | 148 | 4.1363520828444104e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_emitted_triple_grouped | success | 5/0 | 6 | 24 | 5 | 294 | 226 | 4.2708986405365956e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_macro_legacy | success | 4/0 | 0 | 24 | 5 | 228 | 124 | 4.1363520828444104e-05 | macro_not_verified | no |
| public | qedc_mc_004_003_000 | independent | success | 6/0 | 0 | 12 | 0 | 312 | 260 | 3.556820104144808e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | shared_parity | success | 6/0 | 0 | 12 | 0 | 312 | 260 | 3.556820104144808e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | dependent_triples_raw | success | 5/0 | 4 | 30 | 3 | 282 | 170 | 3.9752304528225846e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | dependent_triples_selected | success | 5/0 | 4 | 30 | 3 | 282 | 170 | 3.9752304528225846e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_dependency_simplified | success | 5/0 | 4 | 30 | 3 | 282 | 170 | 3.9752304528225846e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_emitted | success | 6/0 | 18 | 54 | 5 | 438 | 228 | 3.6313455858807336e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_emitted_triple_grouped | success | 7/0 | 12 | 42 | 5 | 448 | 204 | 4.199307109326226e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_macro_legacy | success | 6/0 | 0 | 36 | 5 | 354 | 192 | 3.6313455858807336e-05 | macro_not_verified | no |
| public | qedc_mc_006_003_000 | independent | success | 9/0 | 0 | 18 | 0 | 468 | 260 | 3.600911231375151e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | shared_parity | success | 9/0 | 0 | 18 | 0 | 468 | 260 | 3.600911231375151e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | dependent_triples_raw | success | 8/0 | 4 | 36 | 3 | 444 | 276 | 4.792110460017027e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | dependent_triples_selected | success | 8/0 | 4 | 36 | 3 | 444 | 276 | 4.792110460017027e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | hwp_dependency_simplified | success | 8/0 | 4 | 36 | 3 | 444 | 276 | 4.792110460017027e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | hwp_emitted | success | 8/0 | 24 | 72 | 5 | 584 | 304 | 4.841794114507645e-05 | verified_lowered_compositional | yes |
| public | qedc_mc_008_003_000 | hwp_emitted_triple_grouped | success | 10/0 | 12 | 48 | 5 | 604 | 308 | 4.07168164146239e-05 | verified_lowered_compositional | yes |
| public | qedc_mc_008_003_000 | hwp_macro_legacy | success | 9/0 | 0 | 48 | 7 | 600 | 198 | 4.1085752334066434e-05 | macro_not_verified | no |
| public | qedc_mc_008_003_000 | independent | success | 12/0 | 0 | 24 | 0 | 624 | 260 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | shared_parity | success | 12/0 | 0 | 24 | 0 | 624 | 260 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | dependent_triples_raw | success | 12/0 | 0 | 24 | 0 | 624 | 312 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | dependent_triples_selected | success | 12/0 | 0 | 24 | 0 | 624 | 312 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_dependency_simplified | success | 12/0 | 0 | 24 | 0 | 624 | 312 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_emitted | success | 8/0 | 24 | 72 | 5 | 584 | 304 | 4.841794114507645e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_emitted_triple_grouped | success | 12/0 | 0 | 24 | 0 | 624 | 312 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_macro_legacy | success | 9/0 | 0 | 48 | 7 | 600 | 198 | 4.1085752334066434e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_biclique_3_4 | independent | success | 12/0 | 0 | 24 | 0 | 624 | 312 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | shared_parity | success | 12/0 | 0 | 24 | 0 | 624 | 312 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | dependent_triples_raw | success | 7/0 | 8 | 54 | 3 | 420 | 292 | 4.248990763816844e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | dependent_triples_selected | success | 7/0 | 8 | 54 | 3 | 420 | 292 | 4.248990763816844e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_dependency_simplified | success | 7/0 | 8 | 54 | 3 | 420 | 292 | 4.248990763816844e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_emitted | success | 10/0 | 30 | 90 | 5 | 730 | 380 | 4.17768538469739e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_emitted_triple_grouped | success | 11/0 | 24 | 78 | 5 | 740 | 356 | 4.542452051549629e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_macro_legacy | success | 11/0 | 0 | 60 | 7 | 718 | 262 | 4.6017682524688205e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_clique_6 | independent | success | 15/0 | 0 | 30 | 0 | 840 | 504 | 3.677456910355846e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | shared_parity | success | 15/0 | 0 | 30 | 0 | 840 | 504 | 3.677456910355846e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | dependent_triples_raw | success | 8/0 | 0 | 16 | 0 | 416 | 364 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | dependent_triples_selected | success | 8/0 | 0 | 16 | 0 | 416 | 364 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_dependency_simplified | success | 8/0 | 0 | 16 | 0 | 416 | 364 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_emitted | success | 6/0 | 14 | 48 | 5 | 410 | 212 | 3.6313455858807336e-05 | verified_lowered_compositional | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_emitted_triple_grouped | success | 8/0 | 0 | 16 | 0 | 416 | 364 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_macro_legacy | success | 6/0 | 0 | 32 | 7 | 396 | 128 | 3.9465476452042535e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_cycle_8 | independent | success | 8/0 | 0 | 16 | 0 | 416 | 364 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | shared_parity | success | 8/0 | 0 | 16 | 0 | 416 | 364 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | dependent_triples_raw | success | 3/0 | 2 | 12 | 3 | 164 | 158 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | dependent_triples_selected | success | 3/0 | 2 | 12 | 3 | 164 | 158 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_dependency_simplified | success | 3/0 | 2 | 12 | 3 | 164 | 158 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_emitted | success | 5/0 | 0 | 6 | 0 | 250 | 200 | 4.566566828250607e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_emitted_triple_grouped | success | 4/0 | 6 | 18 | 5 | 242 | 174 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_macro_legacy | success | 4/0 | 0 | 16 | 5 | 228 | 118 | 4.1363520828444104e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_dependent | independent | success | 5/0 | 0 | 6 | 0 | 250 | 200 | 4.566566828250607e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | shared_parity | success | 5/0 | 0 | 6 | 0 | 250 | 200 | 4.566566828250607e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | dependent_triples_raw | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | dependent_triples_selected | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_dependency_simplified | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_emitted | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_emitted_triple_grouped | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_macro_legacy | success | 3/0 | 0 | 10 | 4 | 164 | 106 | 4.717241000082439e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_duplicates | independent | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | shared_parity | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | dependent_triples_raw | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | dependent_triples_selected | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_dependency_simplified | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_emitted | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_emitted_triple_grouped | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_macro_legacy | success | 5/0 | 0 | 28 | 7 | 312 | 128 | 3.99679791292664e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_path_8 | independent | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | shared_parity | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | dependent_triples_raw | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | dependent_triples_selected | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_dependency_simplified | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_emitted | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_emitted_triple_grouped | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_macro_legacy | success | 5/0 | 0 | 28 | 7 | 312 | 128 | 3.99679791292664e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_star_8 | independent | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | shared_parity | success | 7/0 | 0 | 14 | 0 | 364 | 364 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | dependent_triples_raw | success | 1/0 | 2 | 12 | 3 | 58 | 52 | 3.339368342764988e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | dependent_triples_selected | success | 1/0 | 2 | 12 | 3 | 58 | 52 | 3.339368342764988e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_dependency_simplified | success | 1/0 | 2 | 12 | 3 | 58 | 52 | 3.339368342764988e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_emitted | success | 2/0 | 6 | 18 | 5 | 136 | 72 | 4.235113079334664e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_emitted_triple_grouped | success | 2/0 | 6 | 18 | 5 | 136 | 72 | 4.235113079334664e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_macro_legacy | success | 2/0 | 0 | 12 | 5 | 108 | 60 | 4.235113079334664e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_triangle | independent | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.6867877680177285e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | shared_parity | success | 3/0 | 0 | 6 | 0 | 150 | 150 | 4.6867877680177285e-05 | verified_lowered_dense | yes |

## Secondary deployment-policy comparison

For completeness, the selected method uses the configured T-count objective to decide whether to deploy the rewrite or fall back. These win/tie/regression tables evaluate that policy; they do not define or discover the structural tradeoff.

### negative_control

| Baseline | Wins | Ties | Regressions | Matched denominator | Zero-T baselines |
| --- | ---: | ---: | ---: | ---: | ---: |
| independent | 0 | 2 | 0 | 2 | 0 |
| shared_parity | 0 | 2 | 0 | 2 | 0 |
| hwp_emitted | 0 | 2 | 0 | 2 | 0 |
| hwp_emitted_triple_grouped | 0 | 2 | 0 | 2 | 0 |
| hwp_dependency_simplified | 0 | 2 | 0 | 2 | 0 |

Best eligible strong baseline: 0 wins, 2 ties, 0 regressions on 2 matched cases.

### public

| Baseline | Wins | Ties | Regressions | Matched denominator | Zero-T baselines |
| --- | ---: | ---: | ---: | ---: | ---: |
| independent | 3 | 0 | 0 | 3 | 0 |
| shared_parity | 3 | 0 | 0 | 3 | 0 |
| hwp_emitted | 3 | 0 | 0 | 3 | 0 |
| hwp_emitted_triple_grouped | 3 | 0 | 0 | 3 | 0 |
| hwp_dependency_simplified | 0 | 3 | 0 | 3 | 0 |

Best eligible strong baseline: 0 wins, 3 ties, 0 regressions on 3 matched cases.

### synthetic_diagnostic

| Baseline | Wins | Ties | Regressions | Matched denominator | Zero-T baselines |
| --- | ---: | ---: | ---: | ---: | ---: |
| independent | 3 | 5 | 0 | 8 | 0 |
| shared_parity | 3 | 5 | 0 | 8 | 0 |
| hwp_emitted | 3 | 3 | 2 | 8 | 0 |
| hwp_emitted_triple_grouped | 3 | 5 | 0 | 8 | 0 |
| hwp_dependency_simplified | 0 | 8 | 0 | 8 | 0 |

Best eligible strong baseline: 0 wins, 6 ties, 2 regressions on 8 matched cases.

## Structural decision

The rotation-for-arithmetic exchange above is present and measurable. Separately, the raw triple and dependency-simplified HWP artifacts emit the same operation stream on 13 of 13 matched cases.
The current triple construction is therefore subsumed by that HWP representation wherever the streams match. It remains a regression and teaching case, not an M3-W novelty witness.

## Remaining comparison limits

The emitted ordinary-HWP circuit is a correctness-complete out-of-place ANF reference. It is not a competitive reproduction of published in-place or measurement-assisted HWP arithmetic. Catalytic, measured, and joint-synthesis methods remain unverified or unavailable and are not ranked.
