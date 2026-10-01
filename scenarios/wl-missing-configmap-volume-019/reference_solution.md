# Reference solution: wl-missing-configmap-volume-019

**Pod mounts a ConfigMap that does not exist -> stuck ContainerCreating**

**Root cause:** The last change to fraud-detection mounts a ConfigMap named `fraud-rules` that was never created. The kubelet cannot set up the volume, so the pod never starts and the Kafka consumer group has no members. Orders pile up unread. Checkout is unaffected, so the failure is silent.

## How to find it

1. `kubectl get pods`: fraud-detection is stuck in `ContainerCreating`.
2. `kubectl describe pod -l opentelemetry.io/name=fraud-detection`: `FailedMount ... configmap "fraud-rules" not found`.
3. Kafka: consumer group `fraud-detection` has no active members and growing lag.
4. `kubectl rollout history deployment/fraud-detection`: the latest revision added the volume.

## Fix

```bash
kubectl rollout undo deployment/fraud-detection
kubectl rollout status deployment/fraud-detection --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-missing-configmap-volume-019` passes.
