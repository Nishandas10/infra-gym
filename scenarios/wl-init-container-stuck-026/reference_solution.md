# Reference solution: wl-init-container-stuck-026

**Init container waits for a dependency name that never resolves**

**Root cause:** The init container `wait-for-valkey-cart` was changed to wait for `valkey-cart-primary`, a host that does not exist. The init container loops forever and the main container never starts.

## How to find it

1. `kubectl get pods`: cart is `Init:0/1`.
2. `kubectl logs <cart-pod> -c wait-for-valkey-cart`: repeated `waiting for valkey-cart` / name resolution errors.
3. `kubectl get deploy cart -o yaml`: the init command uses `valkey-cart-primary`.
4. `kubectl rollout history deployment/cart` shows the change; rolling back fixes it.

## Fix

```bash
kubectl rollout undo deployment/cart
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-init-container-stuck-026` passes.
