# Reference solution: wl-client-dns-typo-015

**Client configured with a dependency hostname that does not exist**

**Root cause:** The frontend's `CART_ADDR` points at `cart-service:8080`. No Service has that name, so every cart call from the frontend fails DNS resolution. The cart service itself is fine.

## How to find it

1. `kubectl get pods`: everything is Running.
2. `kubectl logs deploy/frontend`: errors resolving `cart-service` (ENOTFOUND / name resolution).
3. `kubectl get svc`: there is no `cart-service`, only `cart`.
4. `kubectl get deploy frontend -o yaml`: `CART_ADDR=cart-service:8080`.

## Fix

```bash
kubectl set env deployment/frontend CART_ADDR=cart:8080
kubectl rollout status deployment/frontend --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-client-dns-typo-015` passes.
