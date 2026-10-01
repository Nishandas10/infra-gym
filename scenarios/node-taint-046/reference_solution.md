# Reference solution: node-taint-046

**Worker nodes tainted; the replacement pod has no toleration**

**Root cause:** Both workers were tainted `dedicated=batch:NoSchedule` to reserve them for batch jobs. The new currency pod has no matching toleration and cannot be scheduled anywhere.

## How to find it

1. `kubectl get pods`: currency `Pending`.
2. `kubectl describe pod -l opentelemetry.io/name=currency`: `untolerated taint {dedicated: batch}`.
3. `kubectl describe nodes | grep Taints`.

## Fix

```bash
kubectl taint nodes ai-gym-worker ai-gym-worker2 dedicated=batch:NoSchedule-
kubectl rollout status deployment/currency --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/node-taint-046` passes.
