# Leaderboard

| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-opus-5-5 | 91.7% | 64.6–98.5% | 11/12 | 11/12 | 0 | 1 | 0 | 17.2 | 220,924 | 0 |
| 2 | gemini-3.8-flash | 8.3% | 1.5–35.4% | 1/12 | 1/12 | 0 | 2 | 0 | 40.0 | 851,791 | 0 |

## Pass rate by family

| family | claude-opus-5-5 | gemini-3.8-flash |
|---|---|---|
| hard | 11/12 (92%) | 1/12 (8%) |

## Pass rate by fault type

| fault_type | claude-opus-5-5 | gemini-3.8-flash |
|---|---|---|
| composite | 9/10 (90%) | 1/10 (10%) |
| create_objects | 1/1 (100%) | 0/1 (0%) |
| flag_in_source_config | 1/1 (100%) | 0/1 (0%) |
