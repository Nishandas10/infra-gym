# Reference solution: valkey-requirepass-076

**Valkey password set; the client does not know it**

**Root cause:** Someone set `requirepass` on valkey-cart. Already-open connections kept working, but after cart restarted it connected without a password and got `NOAUTH Authentication required`.

## How to find it

1. cart logs: `NOAUTH Authentication required`.
2. `kubectl exec deploy/valkey-cart -- valkey-cli PING`: `NOAUTH`.
3. Either remove the password or give cart the credential; the reference fix removes the unauthorised change.

## Fix

```bash
kubectl exec deploy/valkey-cart -- valkey-cli -a rotated-s3cret --no-auth-warning CONFIG SET requirepass ''
kubectl rollout restart deployment/cart
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/valkey-requirepass-076` passes.
