# Mixed linear-cost HWP study

New execution under the [frozen protocol](../docs/hwp-linear-cost-evaluation.md). J uses the supplied raw weights; depth is complete-wave depth. Emitted depth is retained in the raw resource records. Exactness is restricted to the declared finite family. Each timed result includes setup, refinement, search, and verified emission; imports and serialization are excluded. References are separate and were never used as timed seeds.

| Input / weights | Best strong reference J | Exact family J* or incomplete | Method | U | L | U-J* | U-L | Selected (T,D,A) | Time s / status |
|---|---:|---:|---|---:|---:|---:|---:|---|---|
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | rounded_interleaved #1 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 1.408 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | rounded_interleaved #2 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 1.390 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | rounded_interleaved #3 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 1.351 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | rounded_partition_progress #1 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 1.520 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | rounded_partition_progress #2 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 1.520 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | rounded_partition_progress #3 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 1.555 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | native_partition #1 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 0.662 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | native_partition #2 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 0.621 / OPTIMAL |
| native_9 / count_emphasis ('1', '0.1', '1') | 1604/5 | 1604/5 | native_partition #3 | 1604/5 | 1604/5 | 0 | 0 | (310, 68, 4) | 0.623 / OPTIMAL |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | rounded_interleaved #1 | 676 | 561 | 90 | 115 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | rounded_interleaved #2 | 676 | 561 | 90 | 115 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | rounded_interleaved #3 | 676 | 561 | 90 | 115 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | rounded_partition_progress #1 | 676 | 561 | 90 | 115 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | rounded_partition_progress #2 | 676 | 561 | 90 | 115 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | rounded_partition_progress #3 | 676 | 561 | 90 | 115 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | native_partition #1 | 586 | 586 | 0 | 0 | (310, 68, 4) | 0.618 / OPTIMAL |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | native_partition #2 | 586 | 586 | 0 | 0 | (310, 68, 4) | 0.613 / OPTIMAL |
| native_9 / depth_emphasis ('1', '4', '1') | 586 | 586 | native_partition #3 | 586 | 586 | 0 | 0 | (310, 68, 4) | 0.627 / OPTIMAL |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | rounded_interleaved #1 | 2366/5 | 1869/5 | 309/5 | 497/5 | (468, 52, 0) | 3.001 / FEASIBLE |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | rounded_interleaved #2 | 2366/5 | 1869/5 | 309/5 | 497/5 | (468, 52, 0) | 3.001 / FEASIBLE |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | rounded_interleaved #3 | 2366/5 | 1869/5 | 309/5 | 497/5 | (468, 52, 0) | 3.001 / FEASIBLE |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | rounded_partition_progress #1 | 2366/5 | 1856/5 | 309/5 | 102 | (468, 52, 0) | 3.001 / FEASIBLE |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | rounded_partition_progress #2 | 2366/5 | 1856/5 | 309/5 | 102 | (468, 52, 0) | 3.001 / FEASIBLE |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | rounded_partition_progress #3 | 2366/5 | 1856/5 | 309/5 | 102 | (468, 52, 0) | 3.001 / FEASIBLE |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | native_partition #1 | 2057/5 | 2057/5 | 0 | 0 | (354, 174, 1) | 0.660 / OPTIMAL |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | native_partition #2 | 2057/5 | 2057/5 | 0 | 0 | (354, 174, 1) | 0.623 / OPTIMAL |
| native_9 / workspace_emphasis ('1', '0.1', '40') | 2057/5 | 2057/5 | native_partition #3 | 2057/5 | 2057/5 | 0 | 0 | (354, 174, 1) | 0.645 / OPTIMAL |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | rounded_interleaved #1 | 572 | 459 | 66 | 113 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | rounded_interleaved #2 | 572 | 459 | 66 | 113 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | rounded_interleaved #3 | 572 | 459 | 66 | 113 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | rounded_partition_progress #1 | 572 | 459 | 66 | 113 | (468, 52, 0) | 3.004 / FEASIBLE |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | rounded_partition_progress #2 | 572 | 459 | 66 | 113 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | rounded_partition_progress #3 | 572 | 459 | 66 | 113 | (468, 52, 0) | 3.002 / FEASIBLE |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | native_partition #1 | 506 | 506 | 0 | 0 | (310, 68, 4) | 0.666 / OPTIMAL |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | native_partition #2 | 506 | 506 | 0 | 0 | (310, 68, 4) | 0.615 / OPTIMAL |
| native_9 / mixed_emphasis ('1', '2', '15') | 506 | 506 | native_partition #3 | 506 | 506 | 0 | 0 | (310, 68, 4) | 0.621 / OPTIMAL |
| overlap_3 / count_emphasis ('1', '0.1', '1') | 1216/5 | 1216/5 | rounded_interleaved #1 | 1216/5 | 1216/5 | 0 | 0 | (228, 112, 4) | 0.199 / OPTIMAL |
| overlap_3 / count_emphasis ('1', '0.1', '1') | 1216/5 | 1216/5 | rounded_interleaved #2 | 1216/5 | 1216/5 | 0 | 0 | (228, 112, 4) | 0.199 / OPTIMAL |
| overlap_3 / count_emphasis ('1', '0.1', '1') | 1216/5 | 1216/5 | rounded_interleaved #3 | 1216/5 | 1216/5 | 0 | 0 | (228, 112, 4) | 0.199 / OPTIMAL |
| overlap_3 / count_emphasis ('1', '0.1', '1') | 1216/5 | 1216/5 | rounded_partition_progress #1 | 1216/5 | 1216/5 | 0 | 0 | (228, 112, 4) | 0.214 / OPTIMAL |
| overlap_3 / count_emphasis ('1', '0.1', '1') | 1216/5 | 1216/5 | rounded_partition_progress #2 | 1216/5 | 1216/5 | 0 | 0 | (228, 112, 4) | 0.207 / OPTIMAL |
| overlap_3 / count_emphasis ('1', '0.1', '1') | 1216/5 | 1216/5 | rounded_partition_progress #3 | 1216/5 | 1216/5 | 0 | 0 | (228, 112, 4) | 0.203 / OPTIMAL |
| overlap_3 / depth_emphasis ('1', '4', '1') | 680 | 680 | rounded_interleaved #1 | 680 | 680 | 0 | 0 | (228, 112, 4) | 0.282 / OPTIMAL |
| overlap_3 / depth_emphasis ('1', '4', '1') | 680 | 680 | rounded_interleaved #2 | 680 | 680 | 0 | 0 | (228, 112, 4) | 0.283 / OPTIMAL |
| overlap_3 / depth_emphasis ('1', '4', '1') | 680 | 680 | rounded_interleaved #3 | 680 | 680 | 0 | 0 | (228, 112, 4) | 0.284 / OPTIMAL |
| overlap_3 / depth_emphasis ('1', '4', '1') | 680 | 680 | rounded_partition_progress #1 | 680 | 680 | 0 | 0 | (228, 112, 4) | 0.291 / OPTIMAL |
| overlap_3 / depth_emphasis ('1', '4', '1') | 680 | 680 | rounded_partition_progress #2 | 680 | 680 | 0 | 0 | (228, 112, 4) | 0.294 / OPTIMAL |
| overlap_3 / depth_emphasis ('1', '4', '1') | 680 | 680 | rounded_partition_progress #3 | 680 | 680 | 0 | 0 | (228, 112, 4) | 0.311 / OPTIMAL |
| overlap_3 / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_interleaved #1 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.192 / OPTIMAL |
| overlap_3 / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_interleaved #2 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.196 / OPTIMAL |
| overlap_3 / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_interleaved #3 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.190 / OPTIMAL |
| overlap_3 / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_partition_progress #1 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.186 / OPTIMAL |
| overlap_3 / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_partition_progress #2 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.198 / OPTIMAL |
| overlap_3 / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_partition_progress #3 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.189 / OPTIMAL |
| overlap_3 / mixed_emphasis ('1', '2', '15') | 512 | 512 | rounded_interleaved #1 | 512 | 512 | 0 | 0 | (228, 112, 4) | 0.285 / OPTIMAL |
| overlap_3 / mixed_emphasis ('1', '2', '15') | 512 | 512 | rounded_interleaved #2 | 512 | 512 | 0 | 0 | (228, 112, 4) | 0.284 / OPTIMAL |
| overlap_3 / mixed_emphasis ('1', '2', '15') | 512 | 512 | rounded_interleaved #3 | 512 | 512 | 0 | 0 | (228, 112, 4) | 0.289 / OPTIMAL |
| overlap_3 / mixed_emphasis ('1', '2', '15') | 512 | 512 | rounded_partition_progress #1 | 512 | 512 | 0 | 0 | (228, 112, 4) | 0.304 / OPTIMAL |
| overlap_3 / mixed_emphasis ('1', '2', '15') | 512 | 512 | rounded_partition_progress #2 | 512 | 512 | 0 | 0 | (228, 112, 4) | 0.305 / OPTIMAL |
| overlap_3 / mixed_emphasis ('1', '2', '15') | 512 | 512 | rounded_partition_progress #3 | 512 | 512 | 0 | 0 | (228, 112, 4) | 0.315 / OPTIMAL |
| overlap_4_probe / count_emphasis ('1', '0.1', '1') | 1154/5 | 1154/5 | rounded_interleaved #1 | 1154/5 | 1154/5 | 0 | 0 | (216, 108, 4) | 0.208 / OPTIMAL |
| overlap_4_probe / count_emphasis ('1', '0.1', '1') | 1154/5 | 1154/5 | rounded_interleaved #2 | 1154/5 | 1154/5 | 0 | 0 | (216, 108, 4) | 0.170 / OPTIMAL |
| overlap_4_probe / count_emphasis ('1', '0.1', '1') | 1154/5 | 1154/5 | rounded_interleaved #3 | 1154/5 | 1154/5 | 0 | 0 | (216, 108, 4) | 0.174 / OPTIMAL |
| overlap_4_probe / count_emphasis ('1', '0.1', '1') | 1154/5 | 1154/5 | rounded_partition_progress #1 | 1154/5 | 1154/5 | 0 | 0 | (216, 108, 4) | 0.182 / OPTIMAL |
| overlap_4_probe / count_emphasis ('1', '0.1', '1') | 1154/5 | 1154/5 | rounded_partition_progress #2 | 1154/5 | 1154/5 | 0 | 0 | (216, 108, 4) | 0.192 / OPTIMAL |
| overlap_4_probe / count_emphasis ('1', '0.1', '1') | 1154/5 | 1154/5 | rounded_partition_progress #3 | 1154/5 | 1154/5 | 0 | 0 | (216, 108, 4) | 0.175 / OPTIMAL |
| overlap_4_probe / depth_emphasis ('1', '4', '1') | 652 | 652 | rounded_interleaved #1 | 652 | 652 | 0 | 0 | (216, 108, 4) | 0.197 / OPTIMAL |
| overlap_4_probe / depth_emphasis ('1', '4', '1') | 652 | 652 | rounded_interleaved #2 | 652 | 652 | 0 | 0 | (216, 108, 4) | 0.194 / OPTIMAL |
| overlap_4_probe / depth_emphasis ('1', '4', '1') | 652 | 652 | rounded_interleaved #3 | 652 | 652 | 0 | 0 | (216, 108, 4) | 0.191 / OPTIMAL |
| overlap_4_probe / depth_emphasis ('1', '4', '1') | 652 | 652 | rounded_partition_progress #1 | 652 | 652 | 0 | 0 | (216, 108, 4) | 0.208 / OPTIMAL |
| overlap_4_probe / depth_emphasis ('1', '4', '1') | 652 | 652 | rounded_partition_progress #2 | 652 | 652 | 0 | 0 | (216, 108, 4) | 0.200 / OPTIMAL |
| overlap_4_probe / depth_emphasis ('1', '4', '1') | 652 | 652 | rounded_partition_progress #3 | 652 | 652 | 0 | 0 | (216, 108, 4) | 0.203 / OPTIMAL |
| overlap_4_probe / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_interleaved #1 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.143 / OPTIMAL |
| overlap_4_probe / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_interleaved #2 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.154 / OPTIMAL |
| overlap_4_probe / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_interleaved #3 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.145 / OPTIMAL |
| overlap_4_probe / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_partition_progress #1 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.144 / OPTIMAL |
| overlap_4_probe / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_partition_progress #2 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.155 / OPTIMAL |
| overlap_4_probe / workspace_emphasis ('1', '0.1', '40') | 1638/5 | 1638/5 | rounded_partition_progress #3 | 1638/5 | 1638/5 | 0 | 0 | (312, 156, 0) | 0.156 / OPTIMAL |
| overlap_4_probe / mixed_emphasis ('1', '2', '15') | 492 | 492 | rounded_interleaved #1 | 492 | 492 | 0 | 0 | (216, 108, 4) | 0.193 / OPTIMAL |
| overlap_4_probe / mixed_emphasis ('1', '2', '15') | 492 | 492 | rounded_interleaved #2 | 492 | 492 | 0 | 0 | (216, 108, 4) | 0.195 / OPTIMAL |
| overlap_4_probe / mixed_emphasis ('1', '2', '15') | 492 | 492 | rounded_interleaved #3 | 492 | 492 | 0 | 0 | (216, 108, 4) | 0.198 / OPTIMAL |
| overlap_4_probe / mixed_emphasis ('1', '2', '15') | 492 | 492 | rounded_partition_progress #1 | 492 | 492 | 0 | 0 | (216, 108, 4) | 0.202 / OPTIMAL |
| overlap_4_probe / mixed_emphasis ('1', '2', '15') | 492 | 492 | rounded_partition_progress #2 | 492 | 492 | 0 | 0 | (216, 108, 4) | 0.201 / OPTIMAL |
| overlap_4_probe / mixed_emphasis ('1', '2', '15') | 492 | 492 | rounded_partition_progress #3 | 492 | 492 | 0 | 0 | (216, 108, 4) | 0.201 / OPTIMAL |

Native partition is inapplicable to both overlap inputs. Incomplete reference incumbents are upper bounds only. Equal-cost tuples are equal primary-quality outcomes.

| Input / query | Method | Verified incumbent / 3 | Exact optimum / 3 | Median elapsed s | Median time to J* s (successes / 3) |
|---|---|---:|---:|---:|---|
| native_9 / count_emphasis | rounded_interleaved | 3/3 | 3/3 | 1.390 | 1.390 (3/3) |
| native_9 / count_emphasis | rounded_partition_progress | 3/3 | 3/3 | 1.520 | 1.520 (3/3) |
| native_9 / count_emphasis | native_partition | 3/3 | 3/3 | 0.623 | 0.622 (3/3) |
| native_9 / depth_emphasis | rounded_interleaved | 3/3 | 0/3 | 3.002 | n/a (0/3) |
| native_9 / depth_emphasis | rounded_partition_progress | 3/3 | 0/3 | 3.002 | n/a (0/3) |
| native_9 / depth_emphasis | native_partition | 3/3 | 3/3 | 0.618 | 0.617 (3/3) |
| native_9 / workspace_emphasis | rounded_interleaved | 3/3 | 0/3 | 3.001 | n/a (0/3) |
| native_9 / workspace_emphasis | rounded_partition_progress | 3/3 | 0/3 | 3.001 | n/a (0/3) |
| native_9 / workspace_emphasis | native_partition | 3/3 | 3/3 | 0.645 | 0.644 (3/3) |
| native_9 / mixed_emphasis | rounded_interleaved | 3/3 | 0/3 | 3.002 | n/a (0/3) |
| native_9 / mixed_emphasis | rounded_partition_progress | 3/3 | 0/3 | 3.002 | n/a (0/3) |
| native_9 / mixed_emphasis | native_partition | 3/3 | 3/3 | 0.621 | 0.620 (3/3) |
| overlap_3 / count_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.199 | 0.199 (3/3) |
| overlap_3 / count_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.207 | 0.207 (3/3) |
| overlap_3 / depth_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.283 | 0.283 (3/3) |
| overlap_3 / depth_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.294 | 0.294 (3/3) |
| overlap_3 / workspace_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.192 | 0.192 (3/3) |
| overlap_3 / workspace_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.189 | 0.189 (3/3) |
| overlap_3 / mixed_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.285 | 0.285 (3/3) |
| overlap_3 / mixed_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.305 | 0.305 (3/3) |
| overlap_4_probe / count_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.174 | 0.174 (3/3) |
| overlap_4_probe / count_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.182 | 0.182 (3/3) |
| overlap_4_probe / depth_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.194 | 0.194 (3/3) |
| overlap_4_probe / depth_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.203 | 0.203 (3/3) |
| overlap_4_probe / workspace_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.145 | 0.043 (3/3) |
| overlap_4_probe / workspace_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.155 | 0.044 (3/3) |
| overlap_4_probe / mixed_emphasis | rounded_interleaved | 3/3 | 3/3 | 0.195 | 0.195 (3/3) |
| overlap_4_probe / mixed_emphasis | rounded_partition_progress | 3/3 | 3/3 | 0.201 | 0.201 (3/3) |

## Interpretation

Both generic policies certified 27/36 and 27/36 timed queries, respectively. The independent native solver certified all 12 native queries. The generic policies missed the three non-count native optima in every repetition; their displayed U-J* is the measured cost shortfall, while U-L is the remaining certificate gap.

The partition/progress addition did not improve attained cost or certification completion in this study. On completed overlap queries both methods were quick; their small timing differences do not establish a general latency advantage.

Exact family and strong batching costs matched in 12/12 completed input/weight queries. Thus this finite family showed no circuit-cost gain against the declared strong construction reference. The native missed optima remain a search-efficiency limitation, not an unattainable-cost claim.

Maximum timed overrun: 0.004s. Cost gaps and completion are compared within each input and weight query only. The strong batching reference is a local construction comparator, not all published HWP methods.
