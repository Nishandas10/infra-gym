# Calibration: hard-v1 v5

Fix mode, prompt v3, finished episodes only. Diagnosis grades: judge `claude-sonnet-5-5`, rubric v2 (C correct, P partial, W wrong, M missing, ? not graded). Bands use the mean of the models' pass rates: easy >= 2/3, hard <= 1/3; *provisional* below 6 episodes.

## Models

| Model | Episodes | Pass rate (95% CI) | Root cause correct | Fixed + understood | Understood, not fixed | Fixed, cause wrong/unstated |
|---|---|---|---|---|---|---|
| claude-opus-5-5 | 24 | 24/24 (100%; 86%-100%) | 23/24 | 23 | 0 | 0 |
| claude-sonnet-5-5 | 16 | 15/16 (94%; 72%-99%) | 15/16 | 15 | 0 | 0 |
| deepseek-v4-pro | 16 | 12/16 (75%; 50%-90%) | 12/16 | 12 | 0 | 0 |
| gemini-4-argon | 16 | 16/16 (100%; 81%-100%) | 16/16 | 16 | 0 | 0 |
| moonshotai/kimi-k3 | 16 | 12/16 (75%; 50%-90%) | 11/16 | 11 | 0 | 0 |
| openai/gpt-6.1-sol | 16 | 15/16 (94%; 72%-99%) | 15/16 | 15 | 0 | 0 |
| z-ai/glm-5.3 | 16 | 15/16 (94%; 72%-99%) | 12/16 | 12 | 0 | 2 |

## Suite

Bands: 15 easy, 1 medium, 0 hard. Signal: 6 separate the models, 10 all pass, 0 all fail.

## Scenarios

| Scenario | claude-opus-5-5 | claude-sonnet-5-5 | deepseek-v4-pro | gemini-4-argon | moonshotai/kimi-k3 | openai/gpt-6.1-sol | z-ai/glm-5.3 | Mean | Band | Signal | Diagnosis (judge) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hard-fix-reverted-by-cronjob-101 | 1/1 | 1/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | 43% | medium | separates | C / C / P / C / P / P / P |
| hard-mutating-policy-rewrites-pods-131 | 3/3 | 1/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 | 71% | easy | separates | CCC / C / W / C / P / C / P |
| hard-pinned-endpoints-108 | 1/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 71% | easy | separates | C / P / C / C / P / C / C |
| hard-cart-chained-addr-auth-103 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 86% | easy | separates | C / C / P / C / C / C / M |
| hard-egress-policy-blocks-db-102 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 86% | easy | separates | C / C / C / C / W / C / C |
| hard-kafka-consumer-quota-130 | 3/3 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 86% | easy | separates | CCC / C / W / C / C / C / C |
| hard-allowlist-forgets-checkout-106 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| hard-duplicate-env-override-109 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| hard-flag-in-source-of-truth-111 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / M |
| hard-flag-targeting-rule-132 | 3/3 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | PCC / C / C / C / C / C / C |
| hard-ghost-legacy-email-pods-104 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| hard-job-sidecar-never-completes-127 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| hard-masked-second-fault-107 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| hard-oom-fix-blocked-by-limitrange-110 | 3/3 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | CCC / C / C / C / C / C / C |
| hard-silent-ledger-write-denied-105 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / P / C / C |
| hard-telemetry-noise-hides-scheduling-112 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |

Diagnosis column: one letter per episode in attempt order, models in the column order above.
