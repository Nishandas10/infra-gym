# Reference solution: hard-telemetry-noise-hides-scheduling-112

**A loud telemetry outage hides the quiet scheduling failure that is actually hurting customers**

**Root cause:** All worker nodes carry a NoSchedule taint (dedicated=batch) and the currency pod, recreated afterwards, has no toleration, so it is Pending and currency conversion fails. Separately, the collector exports traces to the wrong Jaeger port: loud, real, but it does not affect customers.

## How a careful SRE finds it

1. The currency journey fails; `kubectl get pods -l opentelemetry.io/name=currency` shows Pending.
2. `kubectl describe pod` (or events): 0/3 nodes available, untolerated taint dedicated=batch.
3. `kubectl describe nodes` shows the taint on every worker.
4. Remove the taints (or add a toleration); currency schedules and conversions work. The collector export errors can be fixed separately; they are not what customers see.

## Traps (why this is hard)

- Spending the budget on the collector's export errors (real but not customer-facing).
- Restarting the currency pod (it stays Pending).

## Noise in this scenario (not the cause)

- the trace pipeline is genuinely broken (wrong exporter port), with errors in collector logs

## Fix

```bash
kubectl taint nodes -l '!node-role.kubernetes.io/control-plane' dedicated=batch:NoSchedule-
kubectl rollout status deployment/currency --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-telemetry-noise-hides-scheduling-112` passes.
