# Reference solution: wl-readiness-never-ready-024

**Readiness probe can never succeed -> no endpoints**

**Root cause:** A readiness probe was added that does an HTTP GET on `/healthz`. The cart server only speaks gRPC and has no such endpoint, so the pod is never Ready and the `cart` Service has no endpoints.

## How to find it

1. `kubectl get pods`: cart is Running but `0/1` READY.
2. `kubectl describe pod -l opentelemetry.io/name=cart`: `Readiness probe failed`.
3. `kubectl get endpointslices -l kubernetes.io/service-name=cart`: no ready endpoints.

## Fix

```bash
kubectl patch deployment cart --type=json -p '[{"op":"remove","path":"/spec/template/spec/containers/0/readinessProbe"}]'
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-readiness-never-ready-024` passes.
