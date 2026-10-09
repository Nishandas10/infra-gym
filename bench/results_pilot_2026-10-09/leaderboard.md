# Leaderboard

| Rank | Model | Pass rate | 95% range | Passed / episodes | Avg commands | Avg tokens | Forbidden | Errors/invalid |
|---|---|---|---|---|---|---|---|---|
| 1 | z-ai/glm-5.3-flash | 50.0% | 9.5–90.5% | 1/2 | 25.5 | 138,863 | 0 | 1 |
| 2 | moonshotai/kimi-k3 | 33.3% | 6.1–79.2% | 1/3 | 6.3 | 24,814 | 0 | 0 |
| 3 | nvidia/nemotron-3.5-lightning-30b-a3b | 33.3% | 6.1–79.2% | 1/3 | 23.3 | 179,239 | 0 | 0 |

## Pass rate by family

| family | z-ai/glm-5.3-flash | moonshotai/kimi-k3 | nvidia/nemotron-3.5-lightning-30b-a3b |
|---|---|---|---|
| application | 0/1 (0%) | 0/1 (0%) | 0/1 (0%) |
| platform | 1/1 (100%) | 0/1 (0%) | 1/1 (100%) |
| workload | - | 1/1 (100%) | 0/1 (0%) |

## Pass rate by fault type

| fault_type | z-ai/glm-5.3-flash | moonshotai/kimi-k3 | nvidia/nemotron-3.5-lightning-30b-a3b |
|---|---|---|---|
| create_objects | 1/1 (100%) | 0/1 (0%) | 1/1 (100%) |
| feature_flag | 0/1 (0%) | 0/1 (0%) | 0/1 (0%) |
| workload_patch | - | 1/1 (100%) | 0/1 (0%) |
