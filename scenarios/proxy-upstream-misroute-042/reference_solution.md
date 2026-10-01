# Reference solution: proxy-upstream-misroute-042

**Edge proxy routes shop traffic to the wrong upstream port**

**Root cause:** The Envoy edge proxy builds its routes from environment variables. `FRONTEND_PORT` was set to 8081, so the shop routes go to `frontend:8081`, where nothing listens. The routes for the other tools are unaffected.

## How to find it

1. `curl -i http://localhost:8080/`: `503 upstream connect error`.
2. `kubectl logs deploy/frontend-proxy`: upstream connection failures to frontend.
3. The frontend pod is healthy; `kubectl get deploy frontend-proxy -o yaml`: `FRONTEND_PORT=8081`.

## Fix

```bash
kubectl set env deployment/frontend-proxy FRONTEND_PORT=8080
kubectl rollout status deployment/frontend-proxy --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/proxy-upstream-misroute-042` passes.
