# Reference solution: wl-ephemeral-storage-evicted-027

**Tiny ephemeral-storage limit -> pods evicted over and over**

**Root cause:** The collector DaemonSet got an `ephemeral-storage` limit of 64Ki. Container logs count toward that limit, and the collector's debug exporter logs continuously, so the kubelet evicts the pods soon after they start.

## How to find it

1. `kubectl get pods -l app.kubernetes.io/name=opentelemetry-collector`: pods `Evicted` / constantly new.
2. `kubectl describe pod <evicted-pod>`: `Pod ephemeral local storage usage exceeds the total limit of containers 64Ki`.
3. `kubectl get ds otel-collector-agent -o yaml`: the ephemeral-storage limit.

## Fix

```bash
kubectl patch daemonset otel-collector-agent --type=json -p '[{"op":"remove","path":"/spec/template/spec/containers/0/resources/limits/ephemeral-storage"}]'
kubectl rollout status daemonset/otel-collector-agent --timeout=240s
kubectl delete pods --field-selector=status.phase=Failed
```

## Confirm

`python verifiers/verify.py scenarios/wl-ephemeral-storage-evicted-027` passes.
