# Reference solution: wl-scaled-to-zero-025

**Deployment scaled to zero replicas**

**Root cause:** The checkout Deployment was scaled to 0 replicas (a leftover of a maintenance action), so there is no checkout pod at all.

## How to find it

1. `kubectl get pods`: no checkout pod.
2. `kubectl get deploy checkout`: `0/0` replicas.
3. `kubectl logs deploy/frontend`: checkout calls fail (unavailable / no endpoints).

## Fix

```bash
kubectl scale deployment checkout --replicas=1
kubectl rollout status deployment/checkout --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-scaled-to-zero-025` passes.
