# Leaderboard (hard-v1)

Suite: **hard-v1 v3** (public, 13 instances, hint level page), fingerprint `sha256:cfe650f6dd9f`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 13 of 13 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-opus-5-5 | 92.3% | 66.7–98.6% | 12/13 | 11/13 | 1 | 0 | 0 | 15.6 | 185,189 | 0 |
| 2 | deepseek-v4-pro | 76.9% | 49.7–91.8% | 10/13 | 10/13 | 0 | 1 | 0 | 34.2 | 319,867 | 0 |

## Pass rate by layer

| layer | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| app | 1/1 (100%) | 1/1 (100%) |
| datastore | 1/1 (100%) | 1/1 (100%) |
| node | 1/1 (100%) | 1/1 (100%) |
| service-net | 4/4 (100%) | 4/4 (100%) |
| workload | 5/6 (83%) | 3/6 (50%) |

## Pass rate by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| config-edit | 8/8 (100%) | 6/8 (75%) |
| datastore-cmd | 2/2 (100%) | 1/2 (50%) |
| delete-object | 3/4 (75%) | 2/4 (50%) |
| flag | 1/1 (100%) | 1/1 (100%) |
| node-op | 1/1 (100%) | 1/1 (100%) |
| restart | 2/2 (100%) | 2/2 (100%) |
| rollback | 0/1 (0%) | 0/1 (0%) |

## Pass rate by drivers (an episode counts under each of its values)

| drivers | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| async-path | 2/2 (100%) | 2/2 (100%) |
| fix-is-blocked | 0/1 (0%) | 0/1 (0%) |
| fix-must-be-durable | 1/1 (100%) | 1/1 (100%) |
| fix-must-hold | 1/1 (100%) | 0/1 (0%) |
| fix-reveals-next-fault | 2/2 (100%) | 1/2 (50%) |
| hidden-second-actor | 1/1 (100%) | 0/1 (0%) |
| intermittent | 2/2 (100%) | 2/2 (100%) |
| looks-correct-config | 1/1 (100%) | 1/1 (100%) |
| looks-healthy | 3/3 (100%) | 3/3 (100%) |
| loud-secondary-fault | 1/1 (100%) | 1/1 (100%) |
| misattributed-symptom | 1/1 (100%) | 1/1 (100%) |
| network-path | 1/1 (100%) | 1/1 (100%) |
| partial-fix-trap | 1/1 (100%) | 1/1 (100%) |
| partial-impact | 1/1 (100%) | 1/1 (100%) |
| partial-reachability | 1/1 (100%) | 1/1 (100%) |
| precedence-rules | 1/1 (100%) | 1/1 (100%) |
| prioritization | 1/1 (100%) | 1/1 (100%) |
| recent-change-bias | 1/1 (100%) | 1/1 (100%) |
| red-herring | 6/6 (100%) | 6/6 (100%) |
| sequential-layers | 2/3 (67%) | 1/3 (33%) |
| silent-failure | 2/2 (100%) | 2/2 (100%) |
| silent-rejection | 0/1 (0%) | 0/1 (0%) |
| two-sources-of-config | 1/1 (100%) | 1/1 (100%) |

Errors/invalid = API failures, or the scenario's baseline/fault check misbehaved; excluded from the pass rate. Clean fixes = passed with no collateral change, nothing made worse and no forbidden action. Collateral = changed/created/deleted objects unrelated to the fault (incl. noise objects); made it worse = a shop check that passed during the fault failed after the agent.
