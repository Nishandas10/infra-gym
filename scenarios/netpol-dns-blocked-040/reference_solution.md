# Reference solution: netpol-dns-blocked-040

**Egress policy allows app ports but blocks DNS**

**Root cause:** The egress policy on the frontend allows TCP 8080 to anywhere but nothing else, so DNS (UDP/TCP 53) is blocked. The frontend cannot resolve any service name, so the allowed port never gets used.

## How to find it

1. `kubectl logs deploy/frontend`: name resolution errors (EAI_AGAIN / getaddrinfo).
2. `kubectl get networkpolicy frontend-egress-app-ports -o yaml`: only TCP 8080 is allowed; no rule for port 53.

## Fix

Add a DNS egress rule (UDP and TCP 53) to NetworkPolicy frontend-egress-app-ports, or remove the policy; then restart frontend.

```bash
kubectl delete networkpolicy frontend-egress-app-ports
kubectl rollout restart deployment/frontend
kubectl rollout status deployment/frontend --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/netpol-dns-blocked-040` passes.
