# Reference solution: wl-readonly-rootfs-022

**readOnlyRootFilesystem on a server that writes to disk -> crash**

**Root cause:** image-provider (nginx) was given a read-only root filesystem, but nginx must write its pid file and cache under `/run` and `/var/cache/nginx`. It exits at startup.

## How to find it

1. `kubectl get pods`: image-provider is in `CrashLoopBackOff`.
2. `kubectl logs deploy/image-provider --previous`: `Read-only file system` errors.
3. `kubectl get deploy image-provider -o yaml`: `readOnlyRootFilesystem: true`.

## Fix

```bash
kubectl patch deployment image-provider --type=json -p '[{"op":"remove","path":"/spec/template/spec/containers/0/securityContext/readOnlyRootFilesystem"}]'
kubectl rollout status deployment/image-provider --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-readonly-rootfs-022` passes.
