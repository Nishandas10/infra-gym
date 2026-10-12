# Reference solution: node-cordoned-045

**All worker nodes cordoned; a pod cannot be rescheduled**

**Root cause:** All worker nodes were cordoned for maintenance and never uncordoned. When the cart pod was removed, its replacement had nowhere to be scheduled (the control-plane node is tainted).

## How to find it

1. `kubectl get pods`: cart `Pending`.
2. `kubectl describe pod -l opentelemetry.io/name=cart`: `node(s) were unschedulable`.
3. `kubectl get nodes`: every worker `SchedulingDisabled`.

## Fix

```bash
kubectl uncordon -l '!node-role.kubernetes.io/control-plane'
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/node-cordoned-045` passes.
