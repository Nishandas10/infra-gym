# Reference solution: obs-pii-redaction-removed-069

**PII reaches the tracing backend after the redaction step was removed from the pipeline**

**Root cause:** The services attach raw personal data (customer email, full card number) to spans. Normally the collector's `transform/redact_sensitive_data` and `redaction` processors hash or mask these attributes before export. They were removed from the traces pipeline, so the raw values now reach Jaeger.

## How to find it

1. Jaeger: checkout/payment spans carry `user.email` and `demo.payment.card_number` in clear text.
2. `kubectl get cm otel-collector-agent -o yaml`: the traces pipeline's processors list lacks `transform/redact_sensitive_data` and `redaction`, although both processors are still defined.

## Fix

Put transform/redact_sensitive_data and redaction back into the collector's traces pipeline and restart the collector. In reality, also purge the leaked data and investigate why apps emit raw PII (here, the emitRawPii flag).

```bash
kubectl get configmap otel-collector-agent -o yaml > /tmp/relay.yaml && python3 -c "import sys,yaml; d=yaml.safe_load(open('/tmp/relay.yaml')); c=yaml.safe_load(d['data']['relay']); p=c['service']['pipelines']['traces']['processors']; [p.append(x) for x in ('transform/redact_sensitive_data','redaction') if x not in p]; d['data']['relay']=yaml.safe_dump(c); [d['metadata'].pop(k,None) for k in ('resourceVersion','uid','creationTimestamp','managedFields')]; yaml.safe_dump(d, open('/tmp/relay.yaml','w'))" && kubectl apply -f /tmp/relay.yaml
kubectl rollout restart daemonset/otel-collector-agent
kubectl rollout status daemonset/otel-collector-agent --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/obs-pii-redaction-removed-069` passes.
