# Structural Diagnosis

Config hash: 537016f9ac523c7245bcb5c48f5c7a3a46ea742f83933e0bd8fbc3ab67c78e59

This report is structural. Resource conclusions belong in the run report.

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

Dependent-triple coverage identifies only where the raw rule can run. The main
evaluation separately measures rotations removed and arithmetic, Clifford work,
and workspace added. Fully lowered T metrics assess one realization of that
exchange; the dependency-simplified HWP overlap test assesses novelty.
