# Reference solution: wl-missing-secret-020

**Env var references a Secret that does not exist -> CreateContainerConfigError**

**Root cause:** The email Deployment now reads `SMTP_PASSWORD` from Secret `email-smtp-credentials`, which does not exist, so the container cannot be created. Checkout only logs email failures, so orders still succeed and nobody notices.

## How to find it

1. `kubectl get pods`: email is `CreateContainerConfigError`.
2. `kubectl describe pod -l opentelemetry.io/name=email`: `secret "email-smtp-credentials" not found`.
3. `kubectl logs deploy/checkout`: warnings that the order confirmation could not be sent.

## Fix

```bash
kubectl set env deployment/email SMTP_PASSWORD-
kubectl rollout status deployment/email --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-missing-secret-020` passes.
