# Reference solution: hard-masked-second-fault-107

**Two faults on the checkout path: fixing the first one reveals the second**

**Root cause:** Two independent faults on one request path. checkout calls product-catalog on port 9090 (wrong), and the shipping Service targets port 8888 where nothing listens. Checkout looks up products before it asks shipping for a quote, so only the first fault is visible until it is fixed.

## How a careful SRE finds it

1. checkout logs: failed to get product from product-catalog:9090 (connection refused).
2. Once PRODUCT_CATALOG_ADDR is corrected, checkout still fails, now while getting a shipping quote.
3. `kubectl get svc shipping -o yaml`: targetPort 8888; shipping pods listen on 8080 (endpoints/pod spec).

## Traps (why this is hard)

- Stopping after the first fix without re-testing end to end.

## Noise in this scenario (not the cause)

- Pending GPU backfill pod with FailedScheduling events

## Fix

Set checkout's PRODUCT_CATALOG_ADDR back to product-catalog:8080, then set the shipping Service's targetPort back to 8080.

```bash
kubectl set env deployment/checkout PRODUCT_CATALOG_ADDR=product-catalog:8080
kubectl rollout status deployment/checkout --timeout=300s
kubectl patch service shipping --type=json -p '[{"op":"replace","path":"/spec/ports/0/targetPort","value":8080}]'
```

## Confirm

`python verifiers/verify.py scenarios/hard-masked-second-fault-107` passes.
