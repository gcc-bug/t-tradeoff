# M2-R Reliable Evaluation

Results: results/raw/repair-pilot

This development pilot compares fully lowered unitary circuits under matched operator-norm error and workspace budgets. Legacy macros and unresolved catalytic or measurement-assisted estimates are shown but excluded from primary rankings.

## Status

- success: 104

## Absolute results

| Stratum | Case | Method | Variant or selection | Status | T | T-depth | Workspace | Error bound | Verification | Primary |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| negative_control | negative_irregular_masks | dependent_triples_raw | raw_lexicographic_disjoint | success | 200 | 100 | 0 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 200 | 100 | 0 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_dependency_simplified | triple_weight_bits_simplified | success | 200 | 100 | 0 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_1:0 | success | 200 | 100 | 0 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 200 | 100 | 0 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | hwp_macro_legacy | legacy_formula_macro | success | 200 | 100 | 0 | 4.245637346821135e-05 | verified_lowered_dense | no |
| negative_control | negative_irregular_masks | independent | normalized_independent | success | 200 | 100 | 0 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_irregular_masks | shared_parity | normalized_greedy_anchor_walk | success | 200 | 150 | 0 | 4.245637346821135e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | dependent_triples_raw | raw_lexicographic_disjoint | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_dependency_simplified | triple_weight_bits_simplified | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_1:0 | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | hwp_macro_legacy | legacy_formula_macro | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | no |
| negative_control | negative_weighted_path | independent | normalized_independent | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| negative_control | negative_weighted_path | shared_parity | normalized_greedy_anchor_walk | success | 254 | 254 | 0 | 4.006872019389769e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | dependent_triples_raw | raw_lexicographic_disjoint | success | 214 | 208 | 3 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 214 | 208 | 3 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 214 | 208 | 3 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_3:2 | success | 284 | 148 | 5 | 4.1363520828444104e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 294 | 226 | 5 | 4.2708986405365956e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | hwp_macro_legacy | legacy_formula_macro | success | 228 | 124 | 5 | 4.1363520828444104e-05 | macro_not_verified | no |
| public | qedc_mc_004_003_000 | independent | normalized_independent | success | 312 | 260 | 0 | 3.556820104144808e-05 | verified_lowered_dense | yes |
| public | qedc_mc_004_003_000 | shared_parity | normalized_greedy_anchor_walk | success | 312 | 260 | 0 | 3.556820104144808e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | dependent_triples_raw | raw_lexicographic_disjoint | success | 282 | 170 | 3 | 3.9752304528225846e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 282 | 170 | 3 | 3.9752304528225846e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 282 | 170 | 3 | 3.9752304528225846e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_3:2 | success | 438 | 228 | 5 | 3.6313455858807336e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 448 | 204 | 5 | 4.199307109326226e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | hwp_macro_legacy | legacy_formula_macro | success | 354 | 192 | 5 | 3.6313455858807336e-05 | macro_not_verified | no |
| public | qedc_mc_006_003_000 | independent | normalized_independent | success | 468 | 260 | 0 | 3.600911231375151e-05 | verified_lowered_dense | yes |
| public | qedc_mc_006_003_000 | shared_parity | normalized_greedy_anchor_walk | success | 468 | 260 | 0 | 3.600911231375151e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | dependent_triples_raw | raw_lexicographic_disjoint | success | 444 | 276 | 3 | 4.792110460017027e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 444 | 276 | 3 | 4.792110460017027e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 444 | 276 | 3 | 4.792110460017027e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_3:2 | success | 584 | 304 | 5 | 4.841794114507645e-05 | verified_lowered_compositional | yes |
| public | qedc_mc_008_003_000 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 604 | 308 | 5 | 4.07168164146239e-05 | verified_lowered_compositional | yes |
| public | qedc_mc_008_003_000 | hwp_macro_legacy | legacy_formula_macro | success | 600 | 198 | 7 | 4.1085752334066434e-05 | macro_not_verified | no |
| public | qedc_mc_008_003_000 | independent | normalized_independent | success | 624 | 260 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| public | qedc_mc_008_003_000 | shared_parity | normalized_greedy_anchor_walk | success | 624 | 260 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | dependent_triples_raw | raw_lexicographic_disjoint | success | 624 | 312 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 624 | 312 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 624 | 312 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_3:2 | success | 584 | 304 | 5 | 4.841794114507645e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 624 | 312 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | hwp_macro_legacy | legacy_formula_macro | success | 600 | 198 | 7 | 4.1085752334066434e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_biclique_3_4 | independent | normalized_independent | success | 624 | 312 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_biclique_3_4 | shared_parity | normalized_greedy_anchor_walk | success | 624 | 312 | 0 | 4.801214975166868e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | dependent_triples_raw | raw_lexicographic_disjoint | success | 420 | 292 | 3 | 4.248990763816844e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 420 | 292 | 3 | 4.248990763816844e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 420 | 292 | 3 | 4.248990763816844e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_3:2 | success | 730 | 380 | 5 | 4.17768538469739e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 740 | 356 | 5 | 4.542452051549629e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | hwp_macro_legacy | legacy_formula_macro | success | 718 | 262 | 7 | 4.6017682524688205e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_clique_6 | independent | normalized_independent | success | 840 | 504 | 0 | 3.677456910355846e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_clique_6 | shared_parity | normalized_greedy_anchor_walk | success | 840 | 504 | 0 | 3.677456910355846e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | dependent_triples_raw | raw_lexicographic_disjoint | success | 416 | 364 | 0 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 416 | 364 | 0 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 416 | 364 | 0 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_3:2 | success | 410 | 212 | 5 | 3.6313455858807336e-05 | verified_lowered_compositional | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 416 | 364 | 0 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | hwp_macro_legacy | legacy_formula_macro | success | 396 | 128 | 7 | 3.9465476452042535e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_cycle_8 | independent | normalized_independent | success | 416 | 364 | 0 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_cycle_8 | shared_parity | normalized_greedy_anchor_walk | success | 416 | 364 | 0 | 4.74242680552641e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | dependent_triples_raw | raw_lexicographic_disjoint | success | 164 | 158 | 3 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 164 | 158 | 3 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_dependency_simplified | triple_weight_bits_simplified | success | 164 | 158 | 3 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_1:0 | success | 250 | 200 | 0 | 4.566566828250607e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 242 | 174 | 5 | 3.894802772722448e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | hwp_macro_legacy | legacy_formula_macro | success | 228 | 118 | 5 | 4.1363520828444104e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_dependent | independent | normalized_independent | success | 250 | 200 | 0 | 4.566566828250607e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_dependent | shared_parity | normalized_greedy_anchor_walk | success | 250 | 200 | 0 | 4.566566828250607e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | dependent_triples_raw | raw_lexicographic_disjoint | success | 150 | 150 | 0 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 150 | 150 | 0 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_dependency_simplified | triple_weight_bits_simplified | success | 150 | 150 | 0 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_1:0 | success | 150 | 150 | 0 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 150 | 150 | 0 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | hwp_macro_legacy | legacy_formula_macro | success | 164 | 106 | 4 | 4.717241000082439e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_duplicates | independent | normalized_independent | success | 150 | 150 | 0 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_duplicates | shared_parity | normalized_greedy_anchor_walk | success | 150 | 150 | 0 | 4.702014384050084e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | dependent_triples_raw | raw_lexicographic_disjoint | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_1:0 | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | hwp_macro_legacy | legacy_formula_macro | success | 312 | 128 | 7 | 3.99679791292664e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_path_8 | independent | normalized_independent | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_path_8 | shared_parity | normalized_greedy_anchor_walk | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | dependent_triples_raw | raw_lexicographic_disjoint | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_dependency_simplified | triple_weight_bits_simplified | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_1:0 | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | hwp_macro_legacy | legacy_formula_macro | success | 312 | 128 | 7 | 3.99679791292664e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_star_8 | independent | normalized_independent | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_star_8 | shared_parity | normalized_greedy_anchor_walk | success | 364 | 364 | 0 | 4.149623454835609e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | dependent_triples_raw | raw_lexicographic_disjoint | success | 58 | 52 | 3 | 3.339368342764988e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | dependent_triples_selected | dependent_triples_raw:raw_lexicographic_disjoint:0 | success | 58 | 52 | 3 | 3.339368342764988e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_dependency_simplified | triple_weight_bits_simplified | success | 58 | 52 | 3 | 3.339368342764988e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_emitted | hwp_emitted:reference_anf_out_of_place_cap_3:2 | success | 136 | 72 | 5 | 4.235113079334664e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_emitted_triple_grouped | reference_anf_candidate_triple_groups | success | 136 | 72 | 5 | 4.235113079334664e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | hwp_macro_legacy | legacy_formula_macro | success | 108 | 60 | 5 | 4.235113079334664e-05 | macro_not_verified | no |
| synthetic_diagnostic | diagnostic_triangle | independent | normalized_independent | success | 150 | 150 | 0 | 4.6867877680177285e-05 | verified_lowered_dense | yes |
| synthetic_diagnostic | diagnostic_triangle | shared_parity | normalized_greedy_anchor_walk | success | 150 | 150 | 0 | 4.6867877680177285e-05 | verified_lowered_dense | yes |

## Paired T-count comparisons

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

The raw triple and dependency-simplified HWP artifacts emit the same operation stream on 13 of 13 matched cases.
The current triple construction is therefore subsumed by that HWP representation wherever the streams match. It remains a regression and teaching case, not an M3-W novelty witness.

## Remaining comparison limits

The emitted ordinary-HWP circuit is a correctness-complete out-of-place ANF reference. It is not a competitive reproduction of published in-place or measurement-assisted HWP arithmetic. Catalytic, measured, and joint-synthesis methods remain unverified or unavailable and are not ranked.
