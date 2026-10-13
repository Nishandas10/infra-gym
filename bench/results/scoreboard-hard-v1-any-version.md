# Infra Gym scoreboard (hard-v1-any-version)

Suite: **hard-v1 v1** (public, 12 instances, hint level page), fingerprint `sha256:1c2bee2c865a`.
Matched by scenario id only (--any-version): rows may come from other scenario versions or hint levels than the suite's, so these numbers are not pinned to it.

| Model | Episodes | Diag. (%) | Mit. (%) | E2E (%) | TTD (s) | TTM (s) | Tokens | Clean (%) | Worse | $/solved |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 12 | 100.0 | 91.7 | 91.7 | - | - | 221K | 91.7 | 1 | 0.25 |
| gemini-3.8-flash | 12 | 75.0 | 8.3 | 8.3 | 197 | 252 | 852K | 8.3 | 2 | 4.00 |

Diagnosis judge: claude-opus-5-5. Mitigation is the verifier's PASS, with no LLM involved.
- claude-opus-5-5: 12 episode(s) ran before timing was recorded (no TTD/TTM)
TTD and TTM include the model's own thinking and API time, so faster providers score better.

## Mit. (%) by layer

| layer | claude-opus-5-5 | gemini-3.8-flash |
|---|---|---|
| app | 1/1 (100%) | 0/1 (0%) |
| datastore | 0/1 (0%) | 0/1 (0%) |
| node | 1/1 (100%) | 0/1 (0%) |
| service-net | 4/4 (100%) | 1/4 (25%) |
| workload | 5/5 (100%) | 0/5 (0%) |

## Mit. (%) by fix_type (an episode counts under each of its values)

| fix_type | claude-opus-5-5 | gemini-3.8-flash |
|---|---|---|
| config-edit | 7/7 (100%) | 1/7 (14%) |
| datastore-cmd | 1/2 (50%) | 0/2 (0%) |
| delete-object | 4/4 (100%) | 0/4 (0%) |
| flag | 1/1 (100%) | 0/1 (0%) |
| node-op | 1/1 (100%) | 0/1 (0%) |
| restart | 1/2 (50%) | 1/2 (50%) |
| rollback | 1/1 (100%) | 0/1 (0%) |

## Mit. (%) by drivers (an episode counts under each of its values)

| drivers | claude-opus-5-5 | gemini-3.8-flash |
|---|---|---|
| async-path | 0/1 (0%) | 0/1 (0%) |
| fix-is-blocked | 1/1 (100%) | 0/1 (0%) |
| fix-must-be-durable | 1/1 (100%) | 0/1 (0%) |
| fix-must-hold | 1/1 (100%) | 0/1 (0%) |
| fix-reveals-next-fault | 2/2 (100%) | 0/2 (0%) |
| hidden-second-actor | 1/1 (100%) | 0/1 (0%) |
| intermittent | 2/2 (100%) | 0/2 (0%) |
| looks-correct-config | 1/1 (100%) | 0/1 (0%) |
| looks-healthy | 2/2 (100%) | 0/2 (0%) |
| loud-secondary-fault | 1/1 (100%) | 0/1 (0%) |
| misattributed-symptom | 1/1 (100%) | 1/1 (100%) |
| network-path | 1/1 (100%) | 1/1 (100%) |
| partial-fix-trap | 1/1 (100%) | 0/1 (0%) |
| partial-impact | 1/1 (100%) | 0/1 (0%) |
| partial-reachability | 1/1 (100%) | 0/1 (0%) |
| precedence-rules | 1/1 (100%) | 0/1 (0%) |
| prioritization | 1/1 (100%) | 0/1 (0%) |
| recent-change-bias | 1/1 (100%) | 0/1 (0%) |
| red-herring | 5/6 (83%) | 1/6 (17%) |
| sequential-layers | 3/3 (100%) | 0/3 (0%) |
| silent-failure | 0/1 (0%) | 0/1 (0%) |
| silent-rejection | 1/1 (100%) | 0/1 (0%) |
| two-sources-of-config | 1/1 (100%) | 0/1 (0%) |
