# Reference solution: wl-client-wrong-port-016

**Client configured with the wrong port for a dependency**

**Root cause:** Checkout's `PRODUCT_CATALOG_ADDR` uses port 9090. The product-catalog Service only exposes 8080, so checkout cannot look up product prices. Browsing still works because the frontend uses the right address.

## How to find it

1. `kubectl logs deploy/checkout`: `connection refused` / unavailable for product-catalog.
2. The frontend can reach product-catalog, so the catalog itself is healthy.
3. `kubectl get deploy checkout -o yaml` vs `kubectl get svc product-catalog`: port mismatch 9090 vs 8080.

## Fix

```bash
kubectl set env deployment/checkout PRODUCT_CATALOG_ADDR=product-catalog:8080
kubectl rollout status deployment/checkout --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-client-wrong-port-016` passes.
