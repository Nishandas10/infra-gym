# Infra Gym scoreboard (bench-v1-dev)

Suite: **bench-v1-dev v1** (public, 20 instances, hint level page), fingerprint `sha256:07d2b199a83e`.
Every row matches a member's content hash at hint level page, agent prompt version 2; 20 of 20 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Model | Episodes | Diag. (%) | Mit. (%) | E2E (%) | TTD (s) | TTM (s) | Tokens | Clean (%) | Worse | $/solved |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4-pro | 20 | not judged | 65.0 | not judged | 40 | 90 | 220K | 60.0 | 2 | 0.04 |

Diagnosis judge: none yet (run bench/judge.py). Mitigation is the verifier's PASS, with no LLM involved.
- deepseek-v4-pro: 20 episode(s) not judged yet (Diag./E2E use judged ones only)
TTD and TTM include the model's own thinking and API time, so faster providers score better.

## Mit. (%) by layer

| layer | deepseek-v4-pro |
|---|---|
| app | 0/4 (0%) |
| datastore | 3/3 (100%) |
| node | 1/1 (100%) |
| observability | 1/1 (100%) |
| platform | 0/2 (0%) |
| service-net | 2/2 (100%) |
| workload | 6/7 (86%) |

## Mit. (%) by fix_type (an episode counts under each of its values)

| fix_type | deepseek-v4-pro |
|---|---|
| config-edit | 8/10 (80%) |
| datastore-cmd | 2/2 (100%) |
| delete-object | 2/3 (67%) |
| flag | 0/4 (0%) |
| node-op | 1/1 (100%) |
| restart | 2/4 (50%) |

## Mit. (%) by drivers (an episode counts under each of its values)

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
