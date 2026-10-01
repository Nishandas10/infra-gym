# Reference solution: limitrange-rejects-048

**LimitRange max is lower than a container's limit**

**Root cause:** A LimitRange caps any container at 128Mi of memory. The ad container's limit is 300Mi, so admission rejects the replacement pod.

## How to find it

1. `kubectl get pods`: no ad pod.
2. `kubectl describe rs -l opentelemetry.io/name=ad`: `maximum memory usage per Container is 128Mi, but limit is 300Mi`.
3. `kubectl get limitrange`.

## Fix

```bash
kubectl delete limitrange container-memory-cap
kubectl rollout restart deployment/ad
kubectl rollout status deployment/ad --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/limitrange-rejects-048` passes.
