# Reference solution: wl-cpu-throttle-032

**CPU limit so low the service is throttled into slowness**

**Root cause:** The frontend got a CPU limit of 50m (5% of a core). The CFS scheduler throttles it for most of every 100ms period, so every page is several times slower than usual (the home page 200-500 ms instead of 20-30 ms) even though nothing errors.

## How to find it

1. Latency is high on every page, errors are low, and there are no restarts.
2. `kubectl get deploy frontend -o yaml`: `limits.cpu: 50m`.
3. Container CPU usage is pinned at the limit (Grafana, or kubelet stats); throttling metrics climb.

## Fix

```bash
kubectl patch deployment frontend --type=json -p '[{"op":"remove","path":"/spec/template/spec/containers/0/resources/limits/cpu"}]'
kubectl rollout status deployment/frontend --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-cpu-throttle-032` passes.
