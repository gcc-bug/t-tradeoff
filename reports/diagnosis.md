# Structural Diagnosis

Config hash: `dda5f78245c6d2bedf78d3fb2c20add6f805dd5dae0c662e8156ebde3823ac28`

This report is structural. Resource conclusions belong in the run report; rank alone is not treated as evidence of cheap integer accumulation.

| Case | Terms | Unique | GF(2) rank | Dependencies | Triple coverage | Graph triangles |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| qedc_mc_004_003_000 | 6 | 6 | 3 | 3 | 1.000 | 4 |
| qedc_mc_006_003_000 | 9 | 9 | 5 | 4 | 0.667 | 2 |
| qedc_mc_008_003_000 | 12 | 12 | 7 | 5 | 0.500 | 2 |
| diagnostic_path_8 | 7 | 7 | 7 | 0 | 0.000 | 0 |
| diagnostic_cycle_8 | 8 | 8 | 7 | 1 | 0.000 | 0 |
| diagnostic_star_8 | 7 | 7 | 7 | 0 | 0.000 | 0 |
| diagnostic_triangle | 3 | 3 | 2 | 1 | 1.000 | 1 |
| diagnostic_clique_6 | 15 | 15 | 5 | 10 | 1.000 | 20 |
| diagnostic_biclique_3_4 | 12 | 12 | 6 | 6 | 0.000 | 0 |
| diagnostic_duplicates | 4 | 3 | 2 | 2 | 1.000 | n/a |
| diagnostic_dependent | 5 | 5 | 3 | 2 | 1.000 | n/a |
| negative_weighted_path | 5 | 5 | 5 | 0 | 0.000 | 0 |
| negative_irregular_masks | 4 | 4 | 4 | 0 | 0.000 | n/a |

## Interpretation

The dependent-triple detector has a nonzero opportunity only where `Triple coverage` is nonzero. Duplicate multiplicities and complete graph details are retained in the adjacent JSON file. Weighted controls are expected to reject ordinary equal-angle HWP.
