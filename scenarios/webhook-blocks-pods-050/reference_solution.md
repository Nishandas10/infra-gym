# Reference solution: webhook-blocks-pods-050

**Validating webhook with failurePolicy=Fail and no backend**

**Root cause:** A ValidatingWebhookConfiguration `pod-policy-guard` intercepts every pod creation in the namespace with `failurePolicy: Fail`, but its backend service does not exist. Every pod create is rejected.

## How to find it

1. `kubectl get pods`: no email pod.
2. `kubectl describe rs -l opentelemetry.io/name=email`: `failed calling webhook "pods.policy-guard.gym.local" ... service "policy-guard" not found`.
3. `kubectl get validatingwebhookconfigurations`.

## Fix

```bash
kubectl delete validatingwebhookconfiguration pod-policy-guard
kubectl rollout restart deployment/email
kubectl rollout status deployment/email --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/webhook-blocks-pods-050` passes.
