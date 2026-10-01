# Reference solution: wl-liveness-wrong-port-023

**Liveness probe checks the wrong port -> restart loop**

**Root cause:** A liveness probe was added that checks TCP port 9999; the service listens on 8080. The kubelet kills the healthy container every ~15 seconds.

## How to find it

1. `kubectl get pods -w`: product-catalog restarts repeatedly.
2. `kubectl describe pod -l opentelemetry.io/name=product-catalog`: `Liveness probe failed: dial tcp ...:9999: connection refused`.
3. The app logs show normal startup each time, so it isn't crashing by itself.

## Fix

```bash
kubectl patch deployment product-catalog --type=json -p '[{"op":"remove","path":"/spec/template/spec/containers/0/livenessProbe"}]'
kubectl rollout status deployment/product-catalog --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-liveness-wrong-port-023` passes.
