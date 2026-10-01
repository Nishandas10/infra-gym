# Reference solution: compound-quota-blocks-fix-090

**Broken config plus a quota that blocks the rollout of the fix**

**Root cause:** Two problems. Shipping's `QUOTE_ADDR` points at `quote-svc`, which does not exist. And a ResourceQuota caps the namespace at 10 pods (about 25 already run), so the corrected Deployment's new pod cannot be created: the rollout stalls and the broken pod keeps serving.

## How to find it

1. shipping logs: cannot resolve `quote-svc`.
2. After fixing the env var: `kubectl rollout status` hangs; `kubectl describe rs` shows `exceeded quota: namespace-pod-quota`.
3. Remove/raise the quota, then the fix rolls out.

## Fix

```bash
kubectl delete resourcequota namespace-pod-quota
kubectl set env deployment/shipping QUOTE_ADDR=http://quote:8080
kubectl rollout status deployment/shipping --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/compound-quota-blocks-fix-090` passes.
