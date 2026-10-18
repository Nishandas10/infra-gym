# Oracle episodes

Every bench-eligible scenario played end to end by `python bench/agent_bench.py oracle`: the reference fix run in the agent's sandbox with the agent's permissions, then graded and cleaned up like a model's episode. 0 of 3 are a clean pass.

| Scenario | Result | Problems |
|---|---|---|
| `flag-ad-high-cpu-065` | problem | not fixed<br>not held |
| `kafka-backlog-010` | problem | not fixed<br>not held |
| `pay-unreachable-007` | problem | the world was broken before this episode (helm reset ({'type': 'kafka_lag', 'group': 'fraud-detection', 'max_lag': 200}: consumer group fraud-detection lag 557 (max 200)); hard reset ({'type':); suspect the cleanup of `kafka-backlog-010` |
