# Reference solution: http-replace-059

**HTTP responses from a service replaced with garbage**

**Root cause:** An HTTPChaos experiment rewrites every response from the quote service to the body `not-a-number` with status 200. Shipping cannot parse the quote, so checkout fails, though every HTTP status is OK.

## How to find it

1. shipping logs: failed to parse the quote response.
2. Calling quote directly from a debug pod returns `not-a-number` instead of a price.
3. `kubectl get httpchaos -A`: `quote-http-garbage`.

## Fix

```bash
kubectl delete httpchaos.chaos-mesh.org quote-http-garbage
```

## Confirm

`python verifiers/verify.py scenarios/http-replace-059` passes.
