# Reference solution: svc-selector-mismatch-035

**Service selector matches no pods -> no endpoints**

**Root cause:** The `product-catalog` Service selector was changed to `opentelemetry.io/name=product-catalog-v2`, which no pod carries, so the Service has no endpoints.

## How to find it

1. `kubectl get endpointslices -l kubernetes.io/service-name=product-catalog`: no endpoints.
2. `kubectl get svc product-catalog -o yaml`: selector `product-catalog-v2`.
3. `kubectl get pods --show-labels`: the pod is labelled `product-catalog`.

## Fix

```bash
kubectl patch service product-catalog --type=json -p '[{"op":"replace","path":"/spec/selector","value":{"opentelemetry.io/name":"product-catalog"}}]'
```

## Confirm

`python verifiers/verify.py scenarios/svc-selector-mismatch-035` passes.
