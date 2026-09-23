# Constrained nine-rotation study

All times include setup, search, synthesis and incumbent verification. Imports/startup and serialization are excluded. Cold means a fresh cache and a constrained query; warm first pays a separate equal-budget count query. OPTIMAL certifies scalar cost only; endpoint completion separately certifies the lexicographically smallest optimal resource tuple. Depth below is complete-wave depth, not the separately recorded emitted-circuit depth.

| Cache | Budget s | Method | T=354 / trials | Endpoint certified / trials | Final tuples | Median time to T≤354 s | Median query s |
|---|---:|---|---:|---:|---|---:|---:|
| cold | 1 | original | 0/3 | 0/3 | (468, 52, 0) | — | 1.0007 |
| cold | 1 | ties | 0/3 | 0/3 | (468, 52, 0) | — | 1.0008 |
| cold | 1 | ties_progress | 0/3 | 0/3 | (468, 52, 0) | — | 1.0007 |
| cold | 1 | ties_partition | 0/3 | 0/3 | (468, 52, 0) | — | 1.0009 |
| cold | 1 | combined | 0/3 | 0/3 | (468, 52, 0) | — | 1.0005 |
| cold | 1 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.4886 | 0.4888 |
| cold | 3 | original | 0/3 | 0/3 | (468, 52, 0) | — | 3.0016 |
| cold | 3 | ties | 0/3 | 0/3 | (468, 52, 0) | — | 3.0016 |
| cold | 3 | ties_progress | 0/3 | 0/3 | (468, 52, 0) | — | 3.0021 |
| cold | 3 | ties_partition | 3/3 | 0/3 | (354, 174, 1) | 1.7958 | 3.0017 |
| cold | 3 | combined | 3/3 | 0/3 | (354, 58, 3) | 1.1103 | 3.0006 |
| cold | 3 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.4757 | 0.4759 |
| cold | 10 | original | 3/3 | 0/3 | (354, 58, 3) | 5.8940 | 5.8960 |
| cold | 10 | ties | 3/3 | 0/3 | (354, 58, 3) | 5.9806 | 10.0020 |
| cold | 10 | ties_progress | 3/3 | 0/3 | (354, 58, 3) | 6.7868 | 10.0029 |
| cold | 10 | ties_partition | 3/3 | 0/3 | (354, 58, 3) | 1.7647 | 10.0021 |
| cold | 10 | combined | 3/3 | 0/3 | (354, 58, 3) | 1.0711 | 10.0007 |
| cold | 10 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.4635 | 0.4636 |
| cold | 30 | original | 3/3 | 0/3 | (354, 58, 3) | 5.8261 | 5.8286 |
| cold | 30 | ties | 3/3 | 0/3 | (354, 58, 3) | 5.8417 | 30.0019 |
| cold | 30 | ties_progress | 3/3 | 0/3 | (354, 58, 3) | 6.6976 | 30.0031 |
| cold | 30 | ties_partition | 3/3 | 0/3 | (354, 58, 3) | 1.7495 | 30.0022 |
| cold | 30 | combined | 3/3 | 0/3 | (354, 58, 3) | 1.0035 | 30.0008 |
| cold | 30 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.5011 | 0.5012 |
| warm | 1 | original | 0/3 | 0/3 | (468, 52, 0) | — | 1.0012 |
| warm | 1 | ties | 0/3 | 0/3 | (468, 52, 0) | — | 1.0014 |
| warm | 1 | ties_progress | 0/3 | 0/3 | (468, 52, 0) | — | 1.0013 |
| warm | 1 | ties_partition | 3/3 | 0/3 | (354, 174, 1) | 0.1354 | 1.0002 |
| warm | 1 | combined | 3/3 | 0/3 | (354, 58, 3) | 0.0578 | 1.0001 |
| warm | 1 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.0660 | 0.0662 |
| warm | 3 | original | 0/3 | 0/3 | (468, 52, 0) | — | 3.0017 |
| warm | 3 | ties | 0/3 | 0/3 | (468, 52, 0) | — | 3.0018 |
| warm | 3 | ties_progress | 0/3 | 0/3 | (468, 52, 0) | — | 3.0023 |
| warm | 3 | ties_partition | 3/3 | 0/3 | (354, 116, 2) | 0.1310 | 3.0003 |
| warm | 3 | combined | 3/3 | 0/3 | (354, 58, 3) | 0.0563 | 3.0001 |
| warm | 3 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.0734 | 0.0736 |
| warm | 10 | original | 3/3 | 0/3 | (354, 58, 3) | 5.4417 | 5.4439 |
| warm | 10 | ties | 3/3 | 0/3 | (354, 58, 3) | 5.3019 | 10.0017 |
| warm | 10 | ties_progress | 3/3 | 0/3 | (354, 58, 3) | 6.1457 | 10.0031 |
| warm | 10 | ties_partition | 3/3 | 0/3 | (354, 58, 3) | 0.1284 | 10.0006 |
| warm | 10 | combined | 3/3 | 0/3 | (354, 58, 3) | 0.0561 | 10.0001 |
| warm | 10 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.0663 | 0.0665 |
| warm | 30 | original | 3/3 | 0/3 | (354, 58, 3) | 5.3300 | 5.3319 |
| warm | 30 | ties | 3/3 | 0/3 | (354, 58, 3) | 5.3898 | 30.0018 |
| warm | 30 | ties_progress | 3/3 | 0/3 | (354, 58, 3) | 6.2752 | 30.0038 |
| warm | 30 | ties_partition | 3/3 | 0/3 | (354, 58, 3) | 0.1297 | 30.0006 |
| warm | 30 | combined | 3/3 | 0/3 | (354, 58, 3) | 0.0551 | 30.0002 |
| warm | 30 | partition | 3/3 | 3/3 | (354, 58, 3) | 0.0930 | 0.0931 |

Time-to-target medians include successful trials only; the success fraction alongside them is mandatory. Do not interpret unequal completion as an equal-quality speedup.

The partition comparator uses integer size partitions and independent exact wave packing after checking exchangeability. It covers the supplied native family, including the coupled disjoint-group probes, but rejects overlapping predicates. Strong batching remains a restricted comparator.

| Coupled case | Ancillas | Depth cap | Reference optimum | Original | Combined | Partition | Strong batching |
|---|---:|---:|---|---|---|---|---|
| coordination_3_3 | 1 | 50 | None | None (INFEASIBLE) | None (INFEASIBLE) | None (INFEASIBLE) | None (TIMEOUT) |
| coordination_3_3 | 1 | 60 | (258, 56, 1) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (FEASIBLE) |
| coordination_3_3 | 1 | 100 | (258, 56, 1) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (FEASIBLE) |
| coordination_3_3 | 1 | 109 | (258, 56, 1) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (OPTIMAL) | (258, 56, 1) (FEASIBLE) |
| coordination_3_3 | 1 | 110 | (224, 110, 1) | (224, 110, 1) (OPTIMAL) | (224, 110, 1) (OPTIMAL) | (224, 110, 1) (OPTIMAL) | (224, 110, 1) (FEASIBLE) |
| coordination_3_3 | 1 | 120 | (224, 110, 1) | (224, 110, 1) (OPTIMAL) | (224, 110, 1) (OPTIMAL) | (224, 110, 1) (OPTIMAL) | (224, 110, 1) (FEASIBLE) |
| coordination_3_3 | 2 | 50 | None | None (INFEASIBLE) | None (INFEASIBLE) | None (INFEASIBLE) | None (TIMEOUT) |
| coordination_3_3 | 2 | 60 | (224, 56, 2) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (FEASIBLE) |
| coordination_3_3 | 2 | 100 | (224, 56, 2) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (FEASIBLE) |
| coordination_3_3 | 2 | 109 | (224, 56, 2) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (FEASIBLE) |
| coordination_3_3 | 2 | 110 | (224, 56, 2) | (224, 110, 1) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (FEASIBLE) |
| coordination_3_3 | 2 | 120 | (224, 56, 2) | (224, 110, 1) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (OPTIMAL) | (224, 56, 2) (FEASIBLE) |
| fresh_3_3 | 1 | 50 | None | None (INFEASIBLE) | None (INFEASIBLE) | None (INFEASIBLE) | None (TIMEOUT) |
| fresh_3_3 | 1 | 60 | (264, 54, 1) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (FEASIBLE) |
| fresh_3_3 | 1 | 100 | (264, 54, 1) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (FEASIBLE) |
| fresh_3_3 | 1 | 109 | (264, 54, 1) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (OPTIMAL) | (264, 54, 1) (FEASIBLE) |
| fresh_3_3 | 1 | 110 | (222, 110, 1) | (222, 110, 1) (OPTIMAL) | (222, 110, 1) (OPTIMAL) | (222, 110, 1) (OPTIMAL) | (222, 110, 1) (FEASIBLE) |
| fresh_3_3 | 1 | 120 | (222, 110, 1) | (222, 110, 1) (OPTIMAL) | (222, 110, 1) (OPTIMAL) | (222, 110, 1) (OPTIMAL) | (222, 110, 1) (FEASIBLE) |
| fresh_3_3 | 2 | 50 | None | None (INFEASIBLE) | None (INFEASIBLE) | None (INFEASIBLE) | None (TIMEOUT) |
| fresh_3_3 | 2 | 60 | (222, 56, 2) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (FEASIBLE) |
| fresh_3_3 | 2 | 100 | (222, 56, 2) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (FEASIBLE) |
| fresh_3_3 | 2 | 109 | (222, 56, 2) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (FEASIBLE) |
| fresh_3_3 | 2 | 110 | (222, 56, 2) | (222, 110, 1) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (FEASIBLE) |
| fresh_3_3 | 2 | 120 | (222, 56, 2) | (222, 110, 1) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (OPTIMAL) | (222, 56, 2) (FEASIBLE) |

Maximum deadline overrun: 0.0288s. Atomic calls are charged.

Raw records include complete references, verified plans, incumbent histories, lower/upper bounds, label/queue peaks, source/config hashes, warm-up outcomes, and separately labeled witness/seed diagnostics. This is a finite construction-family experiment, not a published-HWP superiority or global circuit-optimality claim.
