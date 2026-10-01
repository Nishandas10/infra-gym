# Reference solution: wl-bad-command-012

**Container command points at a binary that does not exist**

**Root cause:** The quote Deployment overrides the container command with `/usr/local/bin/quote-server`, which does not exist in the image. The container can never start, so shipping cannot get a price quote and checkout fails two hops away from the real problem.

## How to find it

1. `kubectl logs deploy/checkout`: the shipping quote call fails.
2. `kubectl logs deploy/shipping`: requests to quote fail.
3. `kubectl get pods`: quote is `RunContainerError` / `CrashLoopBackOff`; `kubectl describe` says `exec: "/usr/local/bin/quote-server": no such file or directory`.
4. The Deployment spec has a `command:` override the image does not support.

## Fix

```bash
kubectl patch deployment quote --type=json -p '[{"op":"remove","path":"/spec/template/spec/containers/0/command"}]'
kubectl rollout status deployment/quote --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-bad-command-012` passes.
