# Oracle episodes

Every bench-eligible scenario played end to end by `python bench/agent_bench.py oracle`: the reference fix run in the agent's sandbox with the agent's permissions, then graded and cleaned up like a model's episode. 10 of 10 are a clean pass.

| Scenario | Result | Problems |
|---|---|---|
| `fa-drained-consumer-lag-118` | ok |  |
| `hard-job-sidecar-never-completes-127` | ok |  |
| `hard-kafka-consumer-quota-130` | ok |  |
| `hard-silent-ledger-write-denied-105` | ok |  |
| `kafka-backlog-010` | ok |  |
| `kafka-broker-down-083` | ok |  |
| `kafka-message-too-large-082` | ok |  |
| `netpol-egress-lockdown-039` | ok |  |
| `wl-jvm-heap-over-limit-031` | ok |  |
| `wl-missing-configmap-volume-019` | ok |  |
