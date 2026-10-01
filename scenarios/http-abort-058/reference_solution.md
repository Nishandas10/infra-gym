# Reference solution: http-abort-058

**HTTP requests to a service aborted at layer 7**

**Root cause:** An HTTPChaos experiment aborts every HTTP request to the email service on port 8080, before it reaches the application. That is why the email app's own logs show nothing.

## How to find it

1. checkout logs: sending confirmations fails (connection reset / EOF).
2. The email app logs show no incoming requests at all.
3. `kubectl get httpchaos -A`: `email-http-abort`.

## Fix

```bash
kubectl delete httpchaos.chaos-mesh.org email-http-abort
```

## Confirm

`python verifiers/verify.py scenarios/http-abort-058` passes.
