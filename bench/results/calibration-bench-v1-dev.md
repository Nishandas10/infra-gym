# Calibration: bench-v1-dev v3

Fix mode, prompt v3, finished episodes only. Diagnosis grades: judge `claude-sonnet-5-5`, rubric v2 (C correct, P partial, W wrong, M missing, ? not graded). Bands use the mean of the models' pass rates: easy >= 2/3, hard <= 1/3; *provisional* below 6 episodes.

## Models

| Model | Episodes | Pass rate (95% CI) | Root cause correct | Fixed + understood | Understood, not fixed | Fixed, cause wrong/unstated |
|---|---|---|---|---|---|---|
| claude-opus-5-5 | 20 | 20/20 (100%; 84%-100%) | 20/20 | 20 | 0 | 0 |
| deepseek-v4-pro | 20 | 15/20 (75%; 53%-89%) | 15/20 | 14 | 1 | 0 |

## Suite

Bands: 15 easy, 5 medium, 0 hard. Signal: 5 separate the models, 15 all pass, 0 all fail.

## Scenarios

| Scenario | claude-opus-5-5 | deepseek-v4-pro | Mean | Band | Signal | Diagnosis (judge) |
|---|---|---|---|---|---|---|
| catalog-fail-008 | 1/1 | 0/1 | 50% | medium (provisional) | separates | C / M |
| coredns-rewrite-poison-044 | 1/1 | 0/1 | 50% | medium (provisional) | separates | C / W |
| flag-cart-failure-067 | 1/1 | 0/1 | 50% | medium (provisional) | separates | C / W |
| flag-image-slow-load-071 | 1/1 | 0/1 | 50% | medium (provisional) | separates | C / W |
| pg-password-rotated-079 | 1/1 | 0/1 | 50% | medium (provisional) | separates | C / C |
| k8s-oom-cascade-001 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| kafka-backlog-010 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| limitrange-rejects-048 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| netpol-dns-blocked-040 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| node-taint-046 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| otel-exporter-broken-085 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| pg-lock-held-081 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| pg-revoked-grant-078 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| proxy-upstream-misroute-042 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| wl-client-wrong-port-016 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| wl-crash-invalid-env-013 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| wl-image-pull-011 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| wl-listen-port-drift-014 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |
| wl-readiness-never-ready-024 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / P |
| wl-unschedulable-request-017 | 1/1 | 1/1 | 100% | easy (provisional) | all pass | C / C |

Diagnosis column: one letter per episode in attempt order, models in the column order above.
