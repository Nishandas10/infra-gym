# Reference solution: rollback-configmap-not-versioned-120

**A checkout setting broken in a ConfigMap that rollouts do not version; rolling back does not bring it back**

**Root cause:** Release 3.1.1 moved checkout's PAYMENT_ADDR out of the Deployment into the ConfigMap `checkout-settings` (envFrom), still with the right value payment:8080. Afterwards the ConfigMap was edited in place to payment:8081, and release 3.1.2 (only a version bump) restarted checkout, which picked up the wrong address: every order fails at the payment step. A ConfigMap is not part of a Deployment revision, so `kubectl rollout undo` goes back to 3.1.1, which reads the same edited ConfigMap and stays broken. The ConfigMap value has to be fixed, and checkout restarted because environment variables are read only at start.

## How to find it

1. `kubectl logs deploy/checkout`: the payment call to payment:8081 fails (timeouts, then unavailable).
2. `kubectl rollout history deployment/checkout`: 3.1.1 moved settings to ConfigMap checkout-settings; 3.1.2 differs from 3.1.1 only in its version label.
3. `kubectl get configmap checkout-settings -o yaml`: PAYMENT_ADDR payment:8081.
4. `kubectl get svc payment`: port 8080; the revision before 3.1.1 set PAYMENT_ADDR=payment:8080 directly.

## Noise in this scenario (not the cause)

- Release 3.1.2 went out last, but it only changed the version label; rolling it back changes nothing.

## Fix

Set PAYMENT_ADDR back to payment:8080 in ConfigMap checkout-settings and restart checkout (`kubectl rollout restart deployment/checkout`). Also correct: rolling checkout back to the revision before both releases (it sets PAYMENT_ADDR=payment:8080 directly), or overriding PAYMENT_ADDR=payment:8080 in the Deployment's env. A plain `kubectl rollout undo` (back to 3.1.1) does not fix it, and editing the ConfigMap without a restart does not reach the running pod.

```bash
kubectl patch configmap checkout-settings --type merge -p '{"data":{"PAYMENT_ADDR":"payment:8080"}}'
kubectl rollout restart deployment/checkout
kubectl rollout status deployment/checkout --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/rollback-configmap-not-versioned-120` passes.
