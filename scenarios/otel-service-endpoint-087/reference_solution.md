# Reference solution: otel-service-endpoint-087

**One service exports telemetry to a collector name that does not exist**

**Root cause:** Checkout's `OTEL_EXPORTER_OTLP_ENDPOINT` points at `otel-collector-gateway`, which does not exist. Only checkout's telemetry is lost, which leaves gaps in otherwise healthy traces.

## How to find it

1. Jaeger: no traces for service `checkout`, while others are fine.
2. checkout logs: OTLP export errors resolving `otel-collector-gateway`.
3. `kubectl get deploy checkout -o yaml`: the endpoint.

## Fix

```bash
kubectl set env deployment/checkout 'OTEL_EXPORTER_OTLP_ENDPOINT=http://$(OTEL_COLLECTOR_NAME):4318'
kubectl rollout status deployment/checkout --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/otel-service-endpoint-087` passes.
