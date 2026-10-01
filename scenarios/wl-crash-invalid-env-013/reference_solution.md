# Reference solution: wl-crash-invalid-env-013

**Invalid configuration value makes the service crash at startup**

**Root cause:** `SHIPPING_PORT` was set to `eighty-eighty`. The shipping service cannot parse it into a listen address and exits at startup, so it crash-loops.

## How to find it

1. `kubectl get pods`: shipping is in `CrashLoopBackOff`.
2. `kubectl logs deploy/shipping --previous`: startup error about the port / bind address.
3. `kubectl get deploy shipping -o yaml`: `SHIPPING_PORT` has an invalid value.

## Fix

```bash
kubectl set env deployment/shipping SHIPPING_PORT=8080
kubectl rollout status deployment/shipping --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-crash-invalid-env-013` passes.
