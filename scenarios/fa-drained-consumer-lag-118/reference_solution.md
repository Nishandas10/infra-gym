# Reference solution: fa-drained-consumer-lag-118

**False alarm: the fraud-detection consumer group had no consumers for a few minutes and has since caught up**

**Root cause:** fraud-detection was scaled to zero and back to one a few minutes ago, so the consumer group had no member for about three minutes (until the new pod's JVM started and joined), which fired the alert. The orders that arrived meanwhile (a handful) were consumed as soon as the new pod joined: the group has one active member and its lag is about zero, accounting is unaffected and checkout works. The alert is stale and nothing needs to be changed; who scaled the Deployment is worth a follow-up, but not a change.

## How to find it

1. `kubectl exec deploy/kafka -- /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group fraud-detection`: one consumer, lag 0 or close to it.
2. `kubectl get pods -l opentelemetry.io/name=fraud-detection`: Running, Ready, 0 restarts, a few minutes old.
3. `kubectl get events` / `kubectl describe deployment fraud-detection`: ScalingReplicaSet to 0, then to 1.
4. fraud-detection's logs show it consuming orders again.

## Fix

Nothing to fix. Report that the consumer group was empty while fraud-detection was scaled to zero and back, and has since caught up (lag about 0). Restarting or scaling fraud-detection, resetting offsets or changing Kafka fails the episode.

None: this is a false alarm. The correct response changes nothing and explains why.

## Confirm

`python verifiers/verify.py scenarios/fa-drained-consumer-lag-118` passes.
