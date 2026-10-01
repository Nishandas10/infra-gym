# Reference solution: otel-collector-unscheduled-086

**Collector DaemonSet has a nodeSelector that matches no node**

**Root cause:** The collector DaemonSet now requires nodes labelled `telemetry-tier=dedicated`. No node has that label, so the DaemonSet runs zero pods and every service's telemetry export fails.

## How to find it

1. `kubectl get ds otel-collector-agent`: DESIRED 0.
2. Service logs: OTLP export errors to otel-collector.
3. `kubectl get ds otel-collector-agent -o yaml`: the nodeSelector.

## Fix

```bash
kubectl patch daemonset otel-collector-agent --type=json -p '[{"op":"remove","path":"/spec/template/spec/nodeSelector/telemetry-tier"}]'
kubectl rollout status daemonset/otel-collector-agent --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/otel-collector-unscheduled-086` passes.
