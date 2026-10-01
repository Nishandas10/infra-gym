# Reference solution: coredns-down-043

**Cluster DNS scaled to zero**

**Root cause:** The CoreDNS Deployment in kube-system was scaled to 0. Nothing in the cluster can resolve names. Existing long-lived connections keep working, which makes the outage look partial.

## How to find it

1. Application logs: `no such host` / `EAI_AGAIN` for service names.
2. `kubectl -n kube-system get deploy coredns`: 0 replicas; `kubectl -n kube-system get pods -l k8s-app=kube-dns`: none.
3. Scale it back up.

## Fix

```bash
kubectl -n kube-system scale deployment coredns --replicas=2
kubectl -n kube-system rollout status deployment/coredns --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/coredns-down-043` passes.
