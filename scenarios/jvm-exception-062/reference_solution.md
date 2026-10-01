# Reference solution: jvm-exception-062

**Exception injected into a JVM method at runtime**

**Root cause:** A Chaos Mesh JVMChaos experiment attached a Byteman agent to the running ad JVM and makes `AdServiceImpl.getAds` throw `RuntimeException("ad inventory unavailable")`. The code on disk is unchanged.

## How to find it

1. ad logs: `RuntimeException: ad inventory unavailable` from getAds.
2. No new deploy: `kubectl rollout history deployment/ad`.
3. `kubectl get jvmchaos -A`: `ad-getads-exception`.

## Fix

```bash
kubectl delete jvmchaos.chaos-mesh.org ad-getads-exception
```

## Confirm

`python verifiers/verify.py scenarios/jvm-exception-062` passes.
