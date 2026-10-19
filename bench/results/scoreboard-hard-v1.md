# Infra Gym scoreboard (hard-v1)

Suite: **hard-v1 v4** (public, 16 instances, hint level page), fingerprint `sha256:4485b810be2f`.
Every row matches a member's content hash at hint level page, agent prompt version 3; 16 of 16 members have results. The suite file lists each member's hash; each result row records it as content_hash.

| Model | Episodes | Diag. (%) | Mit. (%) | E2E (%) | TTD (s) | TTM (s) | Tokens | Clean (%) | Worse | $/solved |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 16 | not judged | 100.0 | not judged | 47 | 152 | 235K | 93.8 | 0 | 0.23 |
| deepseek-v4-pro | 16 | not judged | 75.0 | not judged | 76 | 142 | 333K | 75.0 | 1 | 0.05 |

Diagnosis judge: none yet (run bench/judge.py). Mitigation is the verifier's PASS, with no LLM involved.
- claude-opus-5-5: 16 episode(s) not judged yet (Diag./E2E use judged ones only)
- deepseek-v4-pro: 16 episode(s) not judged yet (Diag./E2E use judged ones only)
TTD and TTM include the model's own thinking and API time, so faster providers score better.

## Mit. (%) by layer

| layer | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| app | 2/2 (100%) | 2/2 (100%) |
| datastore | 2/2 (100%) | 1/2 (50%) |
| node | 1/1 (100%) | 1/1 (100%) |
| platform | 1/1 (100%) | 0/1 (0%) |
| service-net | 4/4 (100%) | 4/4 (100%) |
| workload | 6/6 (100%) | 4/6 (67%) |

## Mit. (%) by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| config-edit | 8/8 (100%) | 6/8 (75%) |
| datastore-cmd | 3/3 (100%) | 1/3 (33%) |
| delete-object | 5/5 (100%) | 3/5 (60%) |
| flag | 2/2 (100%) | 2/2 (100%) |
| node-op | 1/1 (100%) | 1/1 (100%) |
| restart | 3/3 (100%) | 2/3 (67%) |
| rollback | 1/1 (100%) | 1/1 (100%) |

## Mit. (%) by drivers (an episode counts under each of its values)

| drivers | claude-opus-5-5 | deepseek-v4-pro |
|---|---|---|
| async-path | 3/3 (100%) | 2/3 (67%) |
| fix-is-blocked | 2/2 (100%) | 1/2 (50%) |
| fix-must-be-durable | 2/2 (100%) | 2/2 (100%) |
| fix-must-hold | 1/1 (100%) | 0/1 (0%) |
| fix-reveals-next-fault | 2/2 (100%) | 1/2 (50%) |
| hidden-second-actor | 2/2 (100%) | 0/2 (0%) |
| intermittent | 3/3 (100%) | 3/3 (100%) |
| looks-correct-config | 3/3 (100%) | 2/3 (67%) |
| looks-healthy | 4/4 (100%) | 3/4 (75%) |
| loud-secondary-fault | 1/1 (100%) | 1/1 (100%) |
| misattributed-symptom | 1/1 (100%) | 1/1 (100%) |
| network-path | 1/1 (100%) | 1/1 (100%) |
| partial-fix-trap | 1/1 (100%) | 1/1 (100%) |
| partial-impact | 2/2 (100%) | 1/2 (50%) |
| partial-reachability | 1/1 (100%) | 1/1 (100%) |
| precedence-rules | 1/1 (100%) | 1/1 (100%) |
| prioritization | 1/1 (100%) | 1/1 (100%) |
| recent-change-bias | 1/1 (100%) | 1/1 (100%) |
| red-herring | 6/6 (100%) | 6/6 (100%) |
| sequential-layers | 3/3 (100%) | 2/3 (67%) |
| silent-failure | 3/3 (100%) | 2/3 (67%) |
| silent-rejection | 1/1 (100%) | 1/1 (100%) |
| two-sources-of-config | 2/2 (100%) | 2/2 (100%) |
