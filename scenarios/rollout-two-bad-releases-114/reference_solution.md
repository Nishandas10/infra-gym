# Reference solution: rollout-two-bad-releases-114

**Two bad shipping releases in a row; rolling back one revision is not enough**

**Root cause:** Two shipping releases went out back to back. 3.1.1 points the quote client at port 8081, so every shipping quote fails and checkout fails with it. 3.1.2 points shipping's OTLP exporter at port 4999 of the collector, so shipping sends no spans at all. A single `kubectl rollout undo` only goes back to 3.1.1, which restores the traces but still has the wrong quote port.

## How to find it

1. `kubectl logs deploy/shipping`: connection refused calling quote:8081, and OTLP export errors.
2. `kubectl rollout history deployment/shipping`: two recent revisions, 3.1.1 and 3.1.2, with change causes.
3. `kubectl rollout history deployment/shipping --revision=<N>`: the revision before both has QUOTE_ADDR http://quote:8080 and the exporter on port 4318.
4. `kubectl get svc quote`: port 8080.

## Fix

Roll shipping back to the revision before both releases (`kubectl rollout history`, then `kubectl rollout undo --to-revision=<N>`). Setting QUOTE_ADDR=http://quote:8080 and OTEL_EXPORTER_OTLP_ENDPOINT=http://$(OTEL_COLLECTOR_NAME):4318 by hand is equally correct. Shipping exports OTLP over HTTP (port 4318), so copying the gRPC endpoint (port 4317) from services such as currency or frontend leaves its traces broken.

```bash
REV=$(kubectl get deploy shipping -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}') && kubectl rollout undo deployment/shipping --to-revision=$((REV - 2))
kubectl rollout status deployment/shipping --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/rollout-two-bad-releases-114` passes.
