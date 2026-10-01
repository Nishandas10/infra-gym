# Reference solution: quota-blocks-pods-047

**ResourceQuota lower than the namespace's pod count**

**Root cause:** A ResourceQuota caps the namespace at 10 pods while about 25 already run. When the shipping pod was replaced, the ReplicaSet could not create the new one.

## How to find it

1. `kubectl get pods`: no shipping pod at all (not even Pending).
2. `kubectl describe rs -l opentelemetry.io/name=shipping`: `FailedCreate ... exceeded quota: namespace-pod-quota`.
3. `kubectl get resourcequota`.

## Fix

```bash
kubectl delete resourcequota namespace-pod-quota
kubectl rollout restart deployment/shipping
kubectl rollout status deployment/shipping --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/quota-blocks-pods-047` passes.
