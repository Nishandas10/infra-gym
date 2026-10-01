# Reference solution: wl-listen-port-drift-014

**Service listens on a different port than its Kubernetes Service targets**

**Root cause:** `PAYMENT_PORT` was changed to 8081, so the payment server now listens on 8081 while the `payment` Service still sends traffic to targetPort 8080. The pod looks perfectly healthy because it has no probes, and every connection to it is refused.

## How to find it

1. `kubectl logs deploy/checkout`: `connection refused` when calling payment.
2. `kubectl logs deploy/payment`: the server says it is listening on port 8081.
3. `kubectl get svc payment -o yaml`: targetPort is 8080, a mismatch.

## Fix

```bash
kubectl set env deployment/payment PAYMENT_PORT=8080
kubectl rollout status deployment/payment --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-listen-port-drift-014` passes.
