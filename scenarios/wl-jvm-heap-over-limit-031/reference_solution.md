# Reference solution: wl-jvm-heap-over-limit-031

**Memory limit below the JVM heap the broker is configured to use**

**Root cause:** The Kafka broker's memory limit was cut to 128Mi, but it runs with `KAFKA_HEAP_OPTS=-Xmx400M -Xms400M`. The JVM needs far more than the limit, so the broker is OOMKilled on every start and crash-loops. Accounting and fraud-detection receive nothing. Checkout's Kafka producer also gets stuck when the broker disappears, so orders start timing out, and it has to be restarted after the broker is fixed.

## How to find it

1. `kubectl get pods`: kafka `CrashLoopBackOff`; `kubectl describe pod` shows `OOMKilled`, exit code 137.
2. `kubectl get deploy kafka -o yaml`: limit 128Mi vs `KAFKA_HEAP_OPTS=-Xmx400M -Xms400M`.
3. accounting/fraud-detection logs: broker unavailable; checkout requests time out.
4. After raising the limit, recreate the `orders` topic if the broker lost it (this demo Kafka has no persistent volume) and restart checkout and the consumers.

## Fix

```bash
kubectl set resources deployment/kafka -c kafka --limits=memory=700Mi
kubectl rollout status deployment/kafka --timeout=300s
for i in $(seq 1 24); do kubectl exec -n gym-system deploy/gym-kafka-tools -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka.default.svc.cluster.local:9092 --create --if-not-exists --topic orders --partitions 1 --replication-factor 1 && break; sleep 5; done
kubectl rollout restart deployment/checkout deployment/accounting deployment/fraud-detection
kubectl rollout status deployment/checkout --timeout=300s
kubectl rollout status deployment/accounting --timeout=300s
kubectl rollout status deployment/fraud-detection --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-jvm-heap-over-limit-031` passes.
