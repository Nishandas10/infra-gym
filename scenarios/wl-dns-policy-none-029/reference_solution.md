# Reference solution: wl-dns-policy-none-029

**Pod DNS set to an unreachable nameserver**

**Root cause:** The checkout pod template sets `dnsPolicy: None` with a nameserver at 192.0.2.53 that does not exist, so checkout cannot resolve any service name. Every dependency fails at once.

## How to find it

1. `kubectl logs deploy/checkout`: every outgoing call fails with name-resolution errors.
2. Other pods resolve names fine, so it is not a cluster-wide DNS outage.
3. `kubectl exec deploy/checkout -- cat /etc/resolv.conf` (or the pod spec): nameserver 192.0.2.53, `dnsPolicy: None`.

## Fix

```bash
kubectl patch deployment checkout --type=json -p '[{"op":"replace","path":"/spec/template/spec/dnsPolicy","value":"ClusterFirst"},{"op":"remove","path":"/spec/template/spec/dnsConfig"}]'
kubectl rollout status deployment/checkout --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-dns-policy-none-029` passes.
