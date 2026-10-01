# Reference solution: svc-targetport-mismatch-036

**Service targetPort points at a port nothing listens on**

**Root cause:** The `shipping` Service's targetPort was changed to 8888. The pod listens on 8080, so connections through the Service are refused while the pod looks perfectly healthy.

## How to find it

1. `kubectl logs deploy/checkout`: connection refused calling shipping.
2. `kubectl get svc shipping -o yaml`: `targetPort: 8888`.
3. `kubectl get endpointslices -l kubernetes.io/service-name=shipping -o yaml`: port 8888.

## Fix

```bash
kubectl patch service shipping --type=json -p '[{"op":"replace","path":"/spec/ports/0/targetPort","value":8080}]'
```

## Confirm

`python verifiers/verify.py scenarios/svc-targetport-mismatch-036` passes.
