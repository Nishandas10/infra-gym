# Leaderboard (bench-v1-dev)

Suite: **bench-v1-dev v2** (public, 20 instances, hint level page), fingerprint `sha256:3dd01bda63a9`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 20 of 20 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-opus-5-5 | 100.0% | 83.9–100.0% | 20/20 | 20/20 | 0 | 0 | 0 | 13.1 | 120,731 | 0 |
| 2 | deepseek-v4-pro | 75.0% | 53.1–88.8% | 15/20 | 15/20 | 0 | 0 | 0 | 27.2 | 204,167 | 0 |

## Pass rate by layer

| layer | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| app | 4/4 (100%) | 1/4 (25%) |
| datastore | 3/3 (100%) | 2/3 (67%) |
| node | 1/1 (100%) | 1/1 (100%) |
| observability | 1/1 (100%) | 1/1 (100%) |
| platform | 2/2 (100%) | 1/2 (50%) |
| service-net | 2/2 (100%) | 2/2 (100%) |
| workload | 7/7 (100%) | 7/7 (100%) |

## Pass rate by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| config-edit | 10/10 (100%) | 9/10 (90%) |
| datastore-cmd | 3/3 (100%) | 2/3 (67%) |
| delete-object | 3/3 (100%) | 3/3 (100%) |
| flag | 4/4 (100%) | 1/4 (25%) |
| node-op | 1/1 (100%) | 1/1 (100%) |
| restart | 4/4 (100%) | 3/4 (75%) |

## Pass rate by drivers (an episode counts under each of its values)

| drivers | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| (none) | 9/9 (100%) | 7/9 (78%) |
| async-path | 1/1 (100%) | 1/1 (100%) |
| looks-correct-config | 1/1 (100%) | 1/1 (100%) |
| looks-healthy | 2/2 (100%) | 2/2 (100%) |
| misattributed-symptom | 2/2 (100%) | 0/2 (0%) |
| partial-fix-trap | 1/1 (100%) | 1/1 (100%) |
| partial-impact | 3/3 (100%) | 2/3 (67%) |
| silent-failure | 1/1 (100%) | 1/1 (100%) |
| silent-rejection | 1/1 (100%) | 1/1 (100%) |

Errors/invalid = API failures, or the scenario's baseline/fault check misbehaved; excluded from the pass rate. Clean fixes = passed with no collateral change, nothing made worse and no forbidden action. Collateral = changed/created/deleted objects unrelated to the fault (incl. noise objects); made it worse = a shop check that passed during the fault failed after the agent.
