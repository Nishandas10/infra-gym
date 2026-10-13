# Reference solution: netpol-default-deny-041

**Namespace-wide default-deny ingress policy**

**Root cause:** A `default-deny-ingress` NetworkPolicy with an empty podSelector blocks all new inbound connections to every pod in the namespace. There are no allow rules to go with it.

## How to find it

1. Requests to frontend-proxy time out; new connections between services time out too.
2. `kubectl get networkpolicy`: `default-deny-ingress` with `podSelector: {}`.

## Fix

Delete NetworkPolicy default-deny-ingress, or add explicit allow policies before enforcing default-deny.

```bash
kubectl delete networkpolicy default-deny-ingress
```

## Confirm

`python verifiers/verify.py scenarios/netpol-default-deny-041` passes.
