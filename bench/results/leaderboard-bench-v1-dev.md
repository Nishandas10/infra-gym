# Leaderboard (bench-v1-dev)

Suite: **bench-v1-dev v1** (public, 20 instances, hint level page), fingerprint `sha256:07d2b199a83e`.
Every row matches a member's content hash at hint level page, agent prompt version 2; 20 of 20 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | deepseek-v4-pro | 65.0% | 43.3–81.9% | 13/20 | 12/20 | 1 | 2 | 0 | 26.9 | 220,092 | 0 |

## Pass rate by layer

| layer | deepseek-v4-pro |
|---|---|
| app | 0/4 (0%) |
| datastore | 3/3 (100%) |
| node | 1/1 (100%) |
| observability | 1/1 (100%) |
| platform | 0/2 (0%) |
| service-net | 2/2 (100%) |
| workload | 6/7 (86%) |

## Pass rate by fix_type (an episode counts under each of its values)

| fix_type | deepseek-v4-pro |
|---|---|
| config-edit | 8/10 (80%) |
| datastore-cmd | 2/2 (100%) |
| delete-object | 2/3 (67%) |
| flag | 0/4 (0%) |
| node-op | 1/1 (100%) |
| restart | 2/4 (50%) |

## Pass rate by drivers (an episode counts under each of its values)

| drivers | deepseek-v4-pro |
|---|---|
| (none) | 9/10 (90%) |
| async-path | 0/1 (0%) |
| looks-correct-config | 1/1 (100%) |
| looks-healthy | 1/2 (50%) |
| misattributed-symptom | 0/2 (0%) |
| partial-impact | 2/3 (67%) |
| silent-failure | 0/1 (0%) |
| silent-rejection | 0/1 (0%) |

Errors/invalid = API failures, or the scenario's baseline/fault check misbehaved; excluded from the pass rate. Clean fixes = passed with no collateral change, nothing made worse and no forbidden action. Collateral = changed/created/deleted objects unrelated to the fault (incl. noise objects); made it worse = a shop check that passed during the fault failed after the agent.
