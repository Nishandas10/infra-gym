# Calibration: hard-v1 v5

Fix mode, prompt v3, finished episodes only. Diagnosis grades: judge `claude-sonnet-5-5`, rubric v2 (C correct, P partial, W wrong, M missing, ? not graded). Bands use the mean of the models' pass rates: easy >= 2/3, hard <= 1/3; *provisional* below 6 episodes.

## Models

| Model | Episodes | Pass rate (95% CI) | Root cause correct | Fixed + understood | Understood, not fixed | Fixed, cause wrong/unstated |
|---|---|---|---|---|---|---|
| claude-opus-5-5 | 24 | 23/24 (96%; 80%-99%) | 22/24 | 22 | 0 | 0 |
| deepseek-v4-pro | 16 | 12/16 (75%; 50%-90%) | 12/16 | 12 | 0 | 0 |

## Suite

Bands: 12 easy, 4 medium, 0 hard. Signal: 4 separate the models, 12 all pass, 0 all fail.

## Scenarios

| Scenario | claude-opus-5-5 | deepseek-v4-pro | Mean | Band | Signal | Diagnosis (judge) |
|---|---|---|---|---|---|---|
| hard-kafka-consumer-quota-130 | 2/3 | 0/1 | 33% | medium (provisional) | separates | CCW / W |
| hard-cart-chained-addr-auth-103 | 1/1 | 0/1 | 50% | medium (provisional) | separates | C / P |
| hard-fix-reverted-by-cronjob-101 | 1/1 | 0/1 | 50% | medium (provisional) | separates | C / P |
| hard-mutating-policy-rewrites-pods-131 | 3/3 | 0/1 | 50% | medium (provisional) | separates | CCC / W |
| hard-allowlist-forgets-checkout-106 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-duplicate-env-override-109 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-egress-policy-blocks-db-102 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-flag-in-source-of-truth-111 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-flag-targeting-rule-132 | 3/3 | 1/1 | 100% | easy (provisional) | all pass | PCC / C |
| hard-ghost-legacy-email-pods-104 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-job-sidecar-never-completes-127 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-masked-second-fault-107 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-oom-fix-blocked-by-limitrange-110 | 3/3 | 1/1 | 100% | easy (provisional) | all pass | CCC / C |
| hard-pinned-endpoints-108 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-silent-ledger-write-denied-105 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| hard-telemetry-noise-hides-scheduling-112 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |

Diagnosis column: one letter per episode in attempt order, models in the column order above.
