# Calibration: bench-v1-dev v3

Fix mode, prompt v3, finished episodes only. Diagnosis grades: judge `claude-sonnet-5-5`, rubric v2 (C correct, P partial, W wrong, M missing, ? not graded). Bands use the mean of the models' pass rates: easy >= 2/3, hard <= 1/3; *provisional* below 6 episodes.

## Models

| Model | Episodes | Pass rate (95% CI) | Root cause correct | Fixed + understood | Understood, not fixed | Fixed, cause wrong/unstated |
|---|---|---|---|---|---|---|
| claude-opus-5-5 | 20 | 20/20 (100%; 84%-100%) | 20/20 | 20 | 0 | 0 |
| claude-sonnet-5-5 | 20 | 18/20 (90%; 70%-97%) | 18/20 | 18 | 0 | 0 |
| deepseek-v4-pro | 21 | 16/21 (76%; 55%-89%) | 16/21 | 15 | 1 | 0 |
| gemini-4-argon | 20 | 20/20 (100%; 84%-100%) | 20/20 | 20 | 0 | 0 |
| moonshotai/kimi-k3 | 20 | 17/20 (85%; 64%-95%) | 18/20 | 17 | 1 | 0 |
| openai/gpt-6.1-sol | 20 | 19/20 (95%; 76%-99%) | 19/20 | 19 | 0 | 0 |
| z-ai/glm-5.3 | 20 | 17/20 (85%; 64%-95%) | 18/20 | 17 | 1 | 0 |

## Suite

Bands: 18 easy, 2 medium, 0 hard. Signal: 7 separate the models, 13 all pass, 0 all fail.

## Scenarios

| Scenario | claude-opus-5-5 | claude-sonnet-5-5 | deepseek-v4-pro | gemini-4-argon | moonshotai/kimi-k3 | openai/gpt-6.1-sol | z-ai/glm-5.3 | Mean | Band | Signal | Diagnosis (judge) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| flag-cart-failure-067 | 1/1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 43% | medium | separates | C / W / W / C / C / W / W |
| coredns-rewrite-poison-044 | 1/1 | 0/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 | 57% | medium | separates | C / M / W / C / W / C / C |
| flag-image-slow-load-071 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 71% | easy | separates | C / C / W / C / C / C / M |
| pg-password-rotated-079 | 1/1 | 1/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 | 71% | easy | separates | C / C / C / C / W / C / C |
| catalog-fail-008 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 86% | easy | separates | C / C / M / C / C / C / C |
| pg-lock-held-081 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 86% | easy | separates | C / C / C / C / C / C / C |
| wl-readiness-never-ready-024 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 86% | easy | separates | C / C / P / C / C / C / C |
| k8s-oom-cascade-001 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| kafka-backlog-010 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| limitrange-rejects-048 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| netpol-dns-blocked-040 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| node-taint-046 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| otel-exporter-broken-085 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| pg-revoked-grant-078 | 1/1 | 1/1 | 2/2 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / CC / C / C / C / C |
| proxy-upstream-misroute-042 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| wl-client-wrong-port-016 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| wl-crash-invalid-env-013 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| wl-image-pull-011 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| wl-listen-port-drift-014 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |
| wl-unschedulable-request-017 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 100% | easy | all pass | C / C / C / C / C / C / C |

Diagnosis column: one letter per episode in attempt order, models in the column order above.
