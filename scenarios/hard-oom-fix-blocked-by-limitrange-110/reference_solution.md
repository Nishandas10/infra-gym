# Reference solution: hard-oom-fix-blocked-by-limitrange-110

**The ad service OOM-loops, and the obvious fix is rejected by a namespace LimitRange**

**Root cause:** Two layers. ad's memory limit was cut to 48Mi, so the JVM is OOMKilled in a loop. Raising the limit to what ad needs is rejected at pod creation by LimitRange namespace-container-limits (max 128Mi), so the new ReplicaSet never gets pods and the old ones keep crashing.

## How a careful SRE finds it

1. ad pods: OOMKilled / CrashLoopBackOff; the memory limit is 48Mi.
2. After raising the limit (e.g. back to the previous revision), `kubectl rollout status` stalls; the new ReplicaSet's events say 'forbidden: maximum memory usage per Container is 128Mi'.
3. `kubectl get limitrange` shows namespace-container-limits, annotated as a temporary cap added with the ad memory tuning (CHG-4412).

## Traps (why this is hard)

- Setting the limit to 128Mi to satisfy the LimitRange: the JVM still does not fit.
- Not reading ReplicaSet events, so the rejection stays invisible.

## Fix

Raise or remove the LimitRange namespace-container-limits, then restore ad's memory limit (for example with `kubectl rollout undo deployment/ad`).

```bash
kubectl delete limitrange namespace-container-limits
kubectl rollout undo deployment/ad
kubectl rollout status deployment/ad --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-oom-fix-blocked-by-limitrange-110` passes.
