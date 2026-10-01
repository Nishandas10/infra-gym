# Reference solution: wl-nodeselector-018

**nodeSelector matches no node -> Pending**

**Root cause:** The ad Deployment was given `nodeSelector: disktype=ssd`. No node carries that label, so the scheduler cannot place the pod.

## How to find it

1. `kubectl get pods`: ad is `Pending`.
2. `kubectl describe pod -l opentelemetry.io/name=ad`: `didn't match Pod's node affinity/selector`.
3. `kubectl get nodes --show-labels`: no node has `disktype=ssd`.

## Fix

```bash
kubectl patch deployment ad --type=json -p '[{"op":"remove","path":"/spec/template/spec/nodeSelector"}]'
kubectl rollout status deployment/ad --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-nodeselector-018` passes.
