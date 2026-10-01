# Reference solution: wl-host-alias-poison-028

**hostAliases entry sends a dependency to a dead IP**

**Root cause:** The frontend pod template has a `hostAliases` entry mapping `product-catalog` to 192.0.2.10 (an unroutable test address), which overrides DNS inside the pod through /etc/hosts. Only the frontend is affected, which is why checkout still works.

## How to find it

1. `kubectl logs deploy/frontend`: timeouts calling product-catalog.
2. Product-catalog is healthy and reachable from other pods (checkout works).
3. `kubectl exec deploy/frontend -- cat /etc/hosts`: `192.0.2.10 product-catalog`.
4. `kubectl get deploy frontend -o yaml`: `hostAliases`.

## Fix

```bash
kubectl patch deployment frontend --type=json -p '[{"op":"remove","path":"/spec/template/spec/hostAliases"}]'
kubectl rollout status deployment/frontend --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-host-alias-poison-028` passes.
