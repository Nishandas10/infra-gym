# Reference solution: wl-run-as-non-root-021

**runAsNonRoot on an image that runs as root -> CreateContainerConfigError**

**Root cause:** Hardening added `runAsNonRoot: true` to the Postgres pod. The postgres image starts as root (its entrypoint drops privileges itself), so the kubelet refuses to start it. With the database gone, product-catalog cannot serve products.

## How to find it

1. `kubectl logs deploy/product-catalog`: database connection errors.
2. `kubectl get pods`: astronomy-db is `CreateContainerConfigError`.
3. `kubectl describe pod -l opentelemetry.io/name=astronomy-db`: `container has runAsNonRoot and image will run as root`.

## Fix

```bash
kubectl patch deployment astronomy-db --type=json -p '[{"op":"remove","path":"/spec/template/spec/securityContext/runAsNonRoot"}]'
kubectl rollout status deployment/astronomy-db --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-run-as-non-root-021` passes.
