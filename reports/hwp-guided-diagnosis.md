# Frozen cost diagnosis

Original study source hashes all match the implementation base. Costs are exact rationals; depth is complete-wave T-depth. Unrestricted means A <= 8. Both reference and model points are filtered by the same limits.

| Input | Queries | Strict wins | Envelope wins | Example constrained T reference → model |
|---|---:|---:|---:|---|
| native_3 | 27 | 0 | 0 | (108, 54, 1) → (108, 54, 1) |
| native_4 | 27 | 0 | 0 | (164, 56, 1) → (164, 56, 1) |
| native_5 | 27 | 0 | 0 | (190, 68, 3) → (190, 68, 3) |
| native_6 | 27 | 0 | 0 | (228, 56, 2) → (228, 56, 2) |
| native_8 | 27 | 0 | 0 | (312, 128, 3) → (312, 128, 3) |
| heterogeneous_3_2 | 27 | 0 | 0 | (210, 56, 1) → (210, 56, 1) |
| overlapping_6 | 27 | 2 | 0 | (312, 156, 0) → (284, 166, 3) |
| qedc_mc_004_003_000 | 27 | 0 | 0 | (312, 156, 0) → (312, 156, 0) |
| distinct_angles_4 | 27 | 0 | 0 | (194, 50, 0) → (194, 50, 0) |
| native_2_holdout | 27 | 0 | 0 | (92, 46, 0) → (92, 46, 0) |
| native_7_holdout | 27 | 0 | 0 | (284, 58, 2) → (284, 58, 2) |
| groups_2_2_2_holdout | 27 | 0 | 0 | (304, 52, 0) → (304, 52, 0) |
| overlap_seed_holdout | 27 | 0 | 0 | (326, 162, 3) → (326, 162, 3) |

The JSON gives the best reference, exact optimum, scales, effective coefficients, and improvement for every cost/limit query. This finite sweep makes no all-weights claim. The overlapping_6 witness (284,166,3) remains a constrained regression; the reference midpoint (270,134,2) dominates it geometrically but is not an executable circuit. H2 remains unestablished for unrestricted costs.
