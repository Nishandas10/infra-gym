# Reference solution: wl-unschedulable-request-017

**Memory request larger than any node -> Pending**

**Root cause:** The recommendation container now requests 64Gi of memory. No node has that much allocatable memory, so the pod stays Pending forever.

## How to find it

1. `kubectl get pods`: recommendation is `Pending`.
2. `kubectl describe pod -l opentelemetry.io/name=recommendation`: `FailedScheduling ... Insufficient memory`.
3. `kubectl get deploy recommendation -o yaml`: requests/limits of 64Gi.

## Fix

```bash
kubectl set resources deployment/recommendation -c recommendation --limits=memory=500Mi --requests=memory=500Mi
kubectl rollout status deployment/recommendation --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-unschedulable-request-017` passes.
