# Reference solution: netpol-egress-lockdown-039

**Egress policy lets a service reach nothing but DNS**

**Root cause:** An egress NetworkPolicy lets checkout pods reach only DNS. Checkout's init container waits for Kafka and can never connect, so the pod stays in `Init:0/1`. Even if it started, every dependency call would be blocked.

## How to find it

1. `kubectl get pods`: checkout is `Init:0/1`.
2. `kubectl logs <checkout-pod> -c wait-for-kafka`: `waiting for kafka` forever (the name resolves; the connection fails).
3. `kubectl get networkpolicy checkout-egress-lockdown -o yaml`: egress allowed only to port 53.

## Fix

```bash
kubectl delete networkpolicy checkout-egress-lockdown
kubectl rollout restart deployment/checkout
kubectl rollout status deployment/checkout --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/netpol-egress-lockdown-039` passes.
