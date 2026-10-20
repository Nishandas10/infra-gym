# Infra Gym scoreboard (bench-v1-dev)

Suite: **bench-v1-dev v3** (public, 20 instances, hint level page), fingerprint `sha256:53eb739bad39`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 20 of 20 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Model | Episodes | Diag. (%) | Mit. (%) | E2E (%) | TTD (s) | TTM (s) | Tokens | Clean (%) | Worse | $/solved |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 20 | 100.0 | 100.0 | 100.0 | 27 | 101 | 123K | 100.0 | 0 | 0.15 |
| gemini-4-argon | 20 | 100.0 | 100.0 | 100.0 | 265 | 416 | 323K | 100.0 | 0 | 0.20 |
| openai/gpt-6.1-sol | 20 | 95.0 | 95.0 | 95.0 | 32 | 89 | 100K | 90.0 | 0 | 0.06 |
| claude-sonnet-5-5 | 20 | 90.0 | 90.0 | 90.0 | 17 | 60 | 63K | 85.0 | 0 | 0.06 |
| moonshotai/kimi-k3 | 20 | 90.0 | 85.0 | 85.0 | 58 | 108 | 131K | 85.0 | 0 | 0.18 |
| z-ai/glm-5.3 | 20 | 90.0 | 85.0 | 85.0 | 24 | 102 | 155K | 85.0 | 0 | 0.11 |
| deepseek-v4-pro | 21 | 76.2 | 76.2 | 71.4 | 51 | 110 | 201K | 76.2 | 0 | 0.04 |

Diagnosis judge: claude-sonnet-5-5. Mitigation is the verifier's PASS, with no LLM involved.
TTD and TTM include the model's own thinking and API time, so faster providers score better.

## Mit. (%) by layer

| layer | claude-opus-5-5 | gemini-4-argon | openai/gpt-6.1-sol | claude-sonnet-5-5 | moonshotai/kimi-k3 | z-ai/glm-5.3 | deepseek-v4-pro |
|---|---|---|---|---|---|---|---|
| app | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 3/4 (75%) | 4/4 (100%) | 2/4 (50%) | 1/4 (25%) |
| datastore | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 2/3 (67%) | 3/4 (75%) |
| node | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| observability | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| platform | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/2 (50%) | 1/2 (50%) | 2/2 (100%) | 1/2 (50%) |
| service-net | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |
| workload | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 6/7 (86%) | 7/7 (100%) | 7/7 (100%) |

## Mit. (%) by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | gemini-4-argon | openai/gpt-6.1-sol | claude-sonnet-5-5 | moonshotai/kimi-k3 | z-ai/glm-5.3 | deepseek-v4-pro |
|---|---|---|---|---|---|---|---|
| config-edit | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) | 9/10 (90%) | 8/10 (80%) | 10/10 (100%) | 9/10 (90%) |
| datastore-cmd | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 2/3 (67%) | 3/4 (75%) |
| delete-object | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 2/3 (67%) | 3/3 (100%) |
| flag | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 3/4 (75%) | 4/4 (100%) | 2/4 (50%) | 1/4 (25%) |
| node-op | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) | 1/1 (100%) |
| restart | 4/4 (100%) | 4/4 (100%) | 4/4 (100%) | 3/4 (75%) | 3/4 (75%) | 4/4 (100%) | 3/4 (75%) |

## Mit. (%) by drivers (an episode counts under each of its values)

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
