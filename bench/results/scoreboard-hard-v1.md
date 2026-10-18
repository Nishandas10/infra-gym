# Infra Gym scoreboard (hard-v1)

Suite: **hard-v1 v3** (public, 13 instances, hint level page), fingerprint `sha256:cfe650f6dd9f`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 13 of 13 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Model | Episodes | Diag. (%) | Mit. (%) | E2E (%) | TTD (s) | TTM (s) | Tokens | Clean (%) | Worse | $/solved |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4-pro | 13 | not judged | 76.9 | not judged | 54 | 122 | 320K | 76.9 | 1 | 0.05 |

Diagnosis judge: none yet (run bench/judge.py). Mitigation is the verifier's PASS, with no LLM involved.
- deepseek-v4-pro: 13 episode(s) not judged yet (Diag./E2E use judged ones only)
TTD and TTM include the model's own thinking and API time, so faster providers score better.

## Mit. (%) by layer

| layer | deepseek-v4-pro |
|---|---|
| app | 1/1 (100%) |
| datastore | 1/1 (100%) |
| node | 1/1 (100%) |
| service-net | 4/4 (100%) |
| workload | 3/6 (50%) |

## Mit. (%) by fix_type (an episode counts under each of its values)

| fix_type | deepseek-v4-pro |
|---|---|
| config-edit | 6/8 (75%) |
| datastore-cmd | 1/2 (50%) |
| delete-object | 2/4 (50%) |
| flag | 1/1 (100%) |
| node-op | 1/1 (100%) |
| restart | 2/2 (100%) |
| rollback | 0/1 (0%) |

## Mit. (%) by drivers (an episode counts under each of its values)

| drivers | deepseek-v4-pro |
|---|---|
| async-path | 2/2 (100%) |
| fix-is-blocked | 0/1 (0%) |
| fix-must-be-durable | 1/1 (100%) |
| fix-must-hold | 0/1 (0%) |
| fix-reveals-next-fault | 1/2 (50%) |
| hidden-second-actor | 0/1 (0%) |
| intermittent | 2/2 (100%) |
| looks-correct-config | 1/1 (100%) |
| looks-healthy | 3/3 (100%) |
| loud-secondary-fault | 1/1 (100%) |
| misattributed-symptom | 1/1 (100%) |
| network-path | 1/1 (100%) |
| partial-fix-trap | 1/1 (100%) |
| partial-impact | 1/1 (100%) |
| partial-reachability | 1/1 (100%) |
| precedence-rules | 1/1 (100%) |
| prioritization | 1/1 (100%) |
| recent-change-bias | 1/1 (100%) |
| red-herring | 6/6 (100%) |
| sequential-layers | 1/3 (33%) |
| silent-failure | 2/2 (100%) |
| silent-rejection | 0/1 (0%) |
| two-sources-of-config | 1/1 (100%) |
