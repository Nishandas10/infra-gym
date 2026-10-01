# Reference solution: kafka-broker-down-083

**Message broker scaled to zero (async pipeline stops silently)**

**Root cause:** The Kafka Deployment was scaled to zero. The consumers (accounting, fraud-detection) sit disconnected, and checkout's Kafka producer gets stuck, so orders eventually time out too.

## How to find it

1. accounting logs: `brokers are down`; checkout requests time out.
2. `kubectl get deploy kafka`: 0 replicas.
3. After restoring the broker, recreate the `orders` topic (no persistent volume in this demo) and restart checkout and the consumers; they do not recover on their own.

## Fix

```bash
kubectl scale deployment kafka --replicas=1
kubectl rollout status deployment/kafka --timeout=300s
for i in $(seq 1 24); do kubectl exec -n gym-system deploy/gym-kafka-tools -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka.default.svc.cluster.local:9092 --create --if-not-exists --topic orders --partitions 1 --replication-factor 1 && break; sleep 5; done
kubectl rollout restart deployment/checkout deployment/accounting deployment/fraud-detection
kubectl rollout status deployment/checkout --timeout=300s
kubectl rollout status deployment/accounting --timeout=300s
kubectl rollout status deployment/fraud-detection --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/kafka-broker-down-083` passes.
