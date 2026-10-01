# Reference solution: otel-exporter-broken-085

**Collector exports traces to the wrong port**

**Root cause:** The collector config's `otlp_grpc/jaeger` exporter endpoint was changed to `jaeger:4999`, where nothing listens. Every trace batch fails to export and is dropped.

## How to find it

1. collector logs: `Exporting failed ... jaeger:4999 ... connection refused`.
2. Jaeger is up, but its newest traces are minutes old.
3. `kubectl get cm otel-collector-agent -o yaml`: the exporter endpoint.

## Fix

```bash
kubectl get configmap otel-collector-agent -o yaml | sed 's/jaeger:4999/jaeger:4317/' | kubectl apply -f -
kubectl rollout restart daemonset/otel-collector-agent
kubectl rollout status daemonset/otel-collector-agent --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/otel-exporter-broken-085` passes.
