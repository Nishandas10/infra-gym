# Reference solution: netpol-ingress-deny-038

**NetworkPolicy blocks all traffic into a service**

**Root cause:** A NetworkPolicy `payment-ingress-lockdown` selects the payment pods and allows no ingress, so checkout's connections to payment are silently dropped (timeouts, not refusals).

## How to find it

1. `kubectl logs deploy/checkout`: payment calls time out.
2. `kubectl get networkpolicy`: `payment-ingress-lockdown` selects the payment pods with no ingress rules.
3. Deleting (or fixing) the policy restores traffic.

## Fix

```bash
kubectl delete networkpolicy payment-ingress-lockdown
```

## Confirm

`python verifiers/verify.py scenarios/netpol-ingress-deny-038` passes.
