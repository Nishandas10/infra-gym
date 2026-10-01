# Reference solution: compound-two-faults-091

**Two unrelated faults at the same time**

**Root cause:** Two independent root causes: recommendation's `PRODUCT_CATALOG_ADDR` uses the wrong port (8081), and the `adFailure` flag is on. Fixing one leaves the other broken; the verifier requires both.

## How to find it

1. recommendation logs: connection refused to product-catalog:8081.
2. ad logs / Feature Flags UI: `adFailure` on.
3. Do not stop after the first fix; re-check both symptoms.

## Fix

```bash
kubectl set env deployment/recommendation PRODUCT_CATALOG_ADDR=product-catalog:8080
kubectl rollout status deployment/recommendation --timeout=300s
python injectors/toggle_flag.py adFailure --off
```

## Confirm

`python verifiers/verify.py scenarios/compound-two-faults-091` passes.
