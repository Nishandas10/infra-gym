# Reference solution: prometheus-otlp-disabled-088

**Prometheus restarted without its OTLP receiver**

**Root cause:** Prometheus was restarted without `--web.enable-otlp-receiver`. The collector pushes metrics over OTLP, and every push is now rejected (404), so no new samples arrive.

## How to find it

1. collector logs: `Exporting failed ... prometheus ... 404`.
2. Prometheus is up, but queries for application metrics return nothing recent.
3. `kubectl get deploy prometheus -o yaml`: the OTLP receiver flag is missing.

## Fix

```bash
kubectl patch deployment prometheus --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--web.enable-otlp-receiver"}]'
kubectl rollout status deployment/prometheus --timeout=240s
```

## Confirm

`python verifiers/verify.py scenarios/prometheus-otlp-disabled-088` passes.
