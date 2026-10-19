# Reference solution: hard-kafka-consumer-quota-130

**New orders stop reaching the ledger; Kafka, accounting and every pod look healthy**

**Root cause:** A Kafka client quota was set on the broker for client id `rdkafka`, which is the accounting service's consumer (librdkafka's default client id). The broker throttles that client to 1 byte per second, so accounting stops making progress on the orders topic and new orders never reach the ledger. Nothing changed in Kubernetes, accounting runs without errors, and fraud-detection (a Java consumer with another client id) keeps up. The quota lives in the broker's dynamic configuration, so restarting accounting does not help.

## How a careful SRE finds it

1. The accounting table stops growing while checkouts succeed.
2. `kafka-consumer-groups.sh --describe --all-groups`: accounting's lag on orders grows every minute; fraud-detection stays at 0. Its CLIENT-ID column says rdkafka.
3. `kafka-configs.sh --describe --entity-type clients`: client-id 'rdkafka' has consumer_byte_rate=1.
4. accounting pods are Running with no restarts and no errors in their logs.

## Traps (why this is hard)

- Restarting accounting or Kafka: the quota survives both.
- Resetting the accounting consumer group's offsets to the latest: the backlog of orders is lost for good.

## Noise in this scenario (not the cause)

- An accounting pod restart (or a Kafka restart) changes nothing: the quota is broker state.

## Fix

Remove the client quota for client id rdkafka on the broker (kafka-configs --alter --entity-type clients --entity-name rdkafka --delete-config consumer_byte_rate). The backlog then drains on its own.

```bash
kubectl exec -n gym-system deploy/gym-kafka-tools -- /opt/kafka/bin/kafka-configs.sh --bootstrap-server kafka.default.svc.cluster.local:9092 --alter --entity-type clients --entity-name rdkafka --delete-config consumer_byte_rate
```

## Confirm

`python verifiers/verify.py scenarios/hard-kafka-consumer-quota-130` passes.
