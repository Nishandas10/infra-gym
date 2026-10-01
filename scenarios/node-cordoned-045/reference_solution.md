# Reference solution: node-cordoned-045

**All worker nodes cordoned; a pod cannot be rescheduled**

**Root cause:** Both worker nodes were cordoned for maintenance and never uncordoned. When the cart pod was removed, its replacement had nowhere to be scheduled (the control-plane node is tainted).

## How to find it

1. `kubectl get pods`: cart `Pending`.
2. `kubectl describe pod -l opentelemetry.io/name=cart`: `node(s) were unschedulable`.
3. `kubectl get nodes`: both workers `SchedulingDisabled`.

## Fix

```bash
kubectl uncordon ai-gym-worker ai-gym-worker2
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/node-cordoned-045` passes.
