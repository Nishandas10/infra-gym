# Infra Gym scoreboard (bench-v1-dev)

Suite: **bench-v1-dev v2** (public, 20 instances, hint level page), fingerprint `sha256:3dd01bda63a9`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 20 of 20 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Model | Episodes | Diag. (%) | Mit. (%) | E2E (%) | TTD (s) | TTM (s) | Tokens | Clean (%) | Worse | $/solved |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 20 | not judged | 100.0 | not judged | 27 | 101 | 121K | 100.0 | 0 | 0.15 |
| deepseek-v4-pro | 20 | not judged | 75.0 | not judged | 53 | 108 | 204K | 75.0 | 0 | 0.04 |

Diagnosis judge: none yet (run bench/judge.py). Mitigation is the verifier's PASS, with no LLM involved.
- claude-opus-5-5: 20 episode(s) not judged yet (Diag./E2E use judged ones only)
- deepseek-v4-pro: 20 episode(s) not judged yet (Diag./E2E use judged ones only)
TTD and TTM include the model's own thinking and API time, so faster providers score better.

## Mit. (%) by layer

| layer | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| app | 4/4 (100%) | 1/4 (25%) |
| datastore | 3/3 (100%) | 2/3 (67%) |
| node | 1/1 (100%) | 1/1 (100%) |
| observability | 1/1 (100%) | 1/1 (100%) |
| platform | 2/2 (100%) | 1/2 (50%) |
| service-net | 2/2 (100%) | 2/2 (100%) |
| workload | 7/7 (100%) | 7/7 (100%) |

## Mit. (%) by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| config-edit | 10/10 (100%) | 9/10 (90%) |
| datastore-cmd | 3/3 (100%) | 2/3 (67%) |
| delete-object | 3/3 (100%) | 3/3 (100%) |
| flag | 4/4 (100%) | 1/4 (25%) |
| node-op | 1/1 (100%) | 1/1 (100%) |
| restart | 4/4 (100%) | 3/4 (75%) |

## Mit. (%) by drivers (an episode counts under each of its values)

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
