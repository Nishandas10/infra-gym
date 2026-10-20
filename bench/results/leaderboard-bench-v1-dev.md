# Leaderboard (bench-v1-dev)

Suite: **bench-v1-dev v3** (public, 20 instances, hint level page), fingerprint `sha256:53eb739bad39`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 20 of 20 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-opus-5-5 | 100.0% | 83.9–100.0% | 20/20 | 20/20 | 0 | 0 | 0 | 13.3 | 123,379 | 0 |
| 2 | gemini-4-argon | 100.0% | 83.9–100.0% | 20/20 | 20/20 | 0 | 0 | 0 | 21.2 | 323,240 | 0 |
| 3 | openai/gpt-6.1-sol | 95.0% | 76.4–99.1% | 19/20 | 18/20 | 1 | 0 | 0 | 12.7 | 99,667 | 0 |
| 4 | claude-sonnet-5-5 | 90.0% | 69.9–97.2% | 18/20 | 17/20 | 1 | 0 | 0 | 8.4 | 62,568 | 0 |
| 5 | moonshotai/kimi-k3 | 85.0% | 64.0–94.8% | 17/20 | 17/20 | 0 | 0 | 0 | 20.4 | 130,770 | 0 |
| 6 | z-ai/glm-5.3 | 85.0% | 64.0–94.8% | 17/20 | 17/20 | 0 | 0 | 0 | 22.5 | 154,935 | 0 |
| 7 | deepseek-v4-pro | 76.2% | 54.9–89.4% | 16/21 | 16/21 | 0 | 0 | 0 | 27.3 | 201,049 | 0 |

## Pass rate by layer

| layer | claude-opus-5-5 | gemini-4-argon | openai/gpt-6.1-sol | claude-sonnet-5-5 | moonshotai/kimi-k3 | z-ai/glm-5.3 | deepseek-v4-pro |
|---|---|---|---|---|---|---|---|
| app | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 3/4 (75%) | 4/4 (100%) | 2/4 (50%) | 1/4 (25%) |
| datastore | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 2/3 (67%) | 3/4 (75%) |
| node | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| observability | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| platform | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 1/2 (50%) | 2/2 (100%) | 1/2 (50%) |
| service-net | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |
| workload | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 6/7 (86%) | 7/7 (100%) | 7/7 (100%) |

## Pass rate by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | gemini-4-argon | openai/gpt-6.1-sol | claude-sonnet-5-5 | moonshotai/kimi-k3 | z-ai/glm-5.3 | deepseek-v4-pro |
|---|---|---|---|---|---|---|---|
| config-edit | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) | 9/10 (90%) | 8/10 (80%) | 10/10 (100%) | 9/10 (90%) |
| datastore-cmd | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 2/3 (67%) | 3/4 (75%) |
| delete-object | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 3/3 (100%) |
| flag | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 3/4 (75%) | 4/4 (100%) | 2/4 (50%) | 1/4 (25%) |
| node-op | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| restart | 4/4 (100%) | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 3/4 (75%) | 4/4 (100%) | 3/4 (75%) |

## Pass rate by drivers (an episode counts under each of its values)

| drivers | claude-opus-5-5 | gemini-4-argon | openai/gpt-6.1-sol | claude-sonnet-5-5 | moonshotai/kimi-k3 | z-ai/glm-5.3 | deepseek-v4-pro |
|---|---|---|---|---|---|---|---|
| (none) | 9/9 (100%) | 9/9 (100%) | 8/9 (89%) | 8/9 (89%) | 8/9 (89%) | 8/9 (89%) | 8/10 (80%) |
| async-path | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| looks-correct-config | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| looks-healthy | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 2/2 (100%) | 2/2 (100%) |
| misattributed-symptom | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 1/2 (50%) | 1/2 (50%) | 0/2 (0%) |
| partial-fix-trap | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 0/1 (0%) | 1/1 (100%) |
| partial-impact | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) |
| silent-failure | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| silent-rejection | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |

Errors/invalid = API failures, or the scenario's baseline/fault check misbehaved; excluded from the pass rate. Clean fixes = passed with no collateral change, nothing made worse and no forbidden action. Collateral = changed/created/deleted objects unrelated to the fault (incl. noise objects); made it worse = a shop check that passed during the fault failed after the agent.
