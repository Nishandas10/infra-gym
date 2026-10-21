# Leaderboard (hard-v1)

Suite: **hard-v1 v5** (public, 16 instances, hint level page), fingerprint `sha256:ebc6818f38ec`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 16 of 16 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-opus-5-5 | 100.0% | 86.2–100.0% | 24/24 | 23/24 | 1 | 0 | 0 | 17.3 | 221,120 | 0 |
| 2 | gemini-4-argon | 100.0% | 80.6–100.0% | 16/16 | 15/16 | 1 | 0 | 0 | 25.9 | 533,415 | 0 |
| 3 | claude-sonnet-5-5 | 93.8% | 71.7–98.9% | 15/16 | 14/16 | 1 | 0 | 0 | 11.8 | 130,714 | 0 |
| 4 | openai/gpt-6.1-sol | 93.8% | 71.7–98.9% | 15/16 | 14/16 | 1 | 0 | 0 | 15.8 | 151,931 | 0 |
| 5 | z-ai/glm-5.3 | 93.8% | 71.7–98.9% | 15/16 | 14/16 | 1 | 0 | 0 | 26.9 | 224,990 | 0 |
| 6 | deepseek-v4-pro | 75.0% | 50.5–89.8% | 12/16 | 12/16 | 0 | 0 | 0 | 35.1 | 334,517 | 0 |
| 7 | moonshotai/kimi-k3 | 75.0% | 50.5–89.8% | 12/16 | 12/16 | 0 | 0 | 0 | 30.2 | 327,719 | 0 |

## Pass rate by layer

| layer | claude-opus-5-5 | gemini-4-argon | claude-sonnet-5-5 | openai/gpt-6.1-sol | z-ai/glm-5.3 | deepseek-v4-pro | moonshotai/kimi-k3 |
|---|---|---|---|---|---|---|---|
| app | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |
| datastore | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 2/2 (100%) |
| node | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| platform | 3/3 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 0/1 (0%) | 0/1 (0%) |
| service-net | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 4/4 (100%) | 4/4 (100%) | 4/4 (100%) | 2/4 (50%) |
| workload | 8/8 (100%) | 6/6 (100%) | 6/6 (100%) | 5/6 (83%) | 5/6 (83%) | 4/6 (67%) | 5/6 (83%) |

## Pass rate by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | gemini-4-argon | claude-sonnet-5-5 | openai/gpt-6.1-sol | z-ai/glm-5.3 | deepseek-v4-pro | moonshotai/kimi-k3 |
|---|---|---|---|---|---|---|---|
| config-edit | 8/8 (100%) | 8/8 (100%) | 7/8 (88%) | 7/8 (88%) | 7/8 (88%) | 6/8 (75%) | 5/8 (62%) |
| datastore-cmd | 5/5 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 1/3 (33%) | 3/3 (100%) |
| delete-object | 9/9 (100%) | 5/5 (100%) | 4/5 (80%) | 4/5 (80%) | 4/5 (80%) | 3/5 (60%) | 2/5 (40%) |
| flag | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |
| node-op | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| restart | 5/5 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 1/3 (33%) |
| rollback | 3/3 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |

## Pass rate by drivers (an episode counts under each of its values)

| drivers | claude-opus-5-5 | gemini-4-argon | claude-sonnet-5-5 | openai/gpt-6.1-sol | z-ai/glm-5.3 | deepseek-v4-pro | moonshotai/kimi-k3 |
|---|---|---|---|---|---|---|---|
| async-path | 5/5 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 3/3 (100%) |
| fix-is-blocked | 6/6 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 1/2 (50%) |
| fix-must-be-durable | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |
| fix-must-hold | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 0/1 (0%) | 0/1 (0%) | 0/1 (0%) | 0/1 (0%) |
| fix-reveals-next-fault | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 2/2 (100%) |
| hidden-second-actor | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 1/2 (50%) | 0/2 (0%) | 0/2 (0%) |
| intermittent | 5/5 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| looks-correct-config | 7/7 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 2/3 (67%) |
| looks-healthy | 6/6 (100%) | 4/4 (100%) | 3/4 (75%) | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 3/4 (75%) |
| loud-secondary-fault | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| misattributed-symptom | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 0/1 (0%) |
| network-path | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 0/1 (0%) |
| partial-fix-trap | 1/1 (100%) | 1/1 (100%) | 0/1 (0%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 0/1 (0%) |
| partial-impact | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 2/2 (100%) |
| partial-reachability | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| precedence-rules | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| prioritization | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| recent-change-bias | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| red-herring | 6/6 (100%) | 6/6 (100%) | 5/6 (83%) | 6/6 (100%) | 6/6 (100%) | 6/6 (100%) | 4/6 (67%) |
| sequential-layers | 5/5 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 3/3 (100%) |
| silent-failure | 5/5 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 3/3 (100%) |
| silent-rejection | 3/3 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| two-sources-of-config | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |

Errors/invalid = API failures, or the scenario's baseline/fault check misbehaved; excluded from the pass rate. Clean fixes = passed with no collateral change, nothing made worse and no forbidden action. Collateral = changed/created/deleted objects unrelated to the fault (incl. noise objects); made it worse = a shop check that passed during the fault failed after the agent.
