# Reference solution: wl-paused-rollout-trap-030

**Bad config plus a paused Deployment: the fix does not roll out**

**Root cause:** Cart's `VALKEY_ADDR` was pointed at `valkey-cart-v2`, which does not exist. The Deployment was then paused, so any corrected template, including the colleague's fix, is recorded but never rolled out.

## How to find it

1. `kubectl logs deploy/cart`: cannot connect to `valkey-cart-v2`.
2. `kubectl get deploy cart -o yaml`: `paused: true`; `kubectl rollout status` says the rollout is paused.
3. After fixing the env var, `kubectl rollout resume deployment/cart` is needed for it to take effect.

## Fix

```bash
kubectl set env deployment/cart VALKEY_ADDR=valkey-cart:6379
kubectl rollout resume deployment/cart
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-paused-rollout-trap-030` passes.
