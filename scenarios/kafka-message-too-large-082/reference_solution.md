# Reference solution: kafka-message-too-large-082

**Topic max message size below the size of real messages**

**Root cause:** The `orders` topic got `max.message.bytes=128`. Every order event is larger, so the broker rejects it (`RecordTooLargeException`). Checkout publishes asynchronously and only logs the error, so orders succeed while the downstream consumers receive nothing.

## How to find it

1. checkout logs: producer errors `The request included a message larger than the max message size`.
2. Consumer lag is not growing (nothing is produced), which rules out slow consumers.
3. `kafka-configs.sh --describe --entity-type topics --entity-name orders`: max.message.bytes=128.

## Fix

```bash
kubectl exec -n gym-system deploy/gym-kafka-tools -- /opt/kafka/bin/kafka-configs.sh --bootstrap-server kafka.default.svc.cluster.local:9092 --alter --entity-type topics --entity-name orders --delete-config max.message.bytes
```

## Confirm

`python verifiers/verify.py scenarios/kafka-message-too-large-082` passes.
