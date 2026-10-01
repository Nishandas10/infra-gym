# Reference solution: grafana-datasource-089

**Grafana's Prometheus datasource points at the wrong port**

**Root cause:** The provisioned Prometheus datasource URL was changed to port 9099, where nothing listens, so Grafana's queries time out while Prometheus and the data are fine. The datasource sidecar applies ConfigMap edits to Grafana live, so fixing the ConfigMap is enough; no restart is needed.

## How to find it

1. Grafana > Connections > Data sources > Prometheus > Test: the query to :9099 times out.
2. `kubectl get cm grafana-datasources -o yaml`: the URL.
3. `kubectl logs deploy/grafana -c grafana-sc-datasources`: it wrote the new file and Grafana reloaded it.
4. Prometheus answers on :9090 directly.

## Fix

```bash
kubectl get configmap grafana-datasources -o yaml | sed 's|prometheus:9099|prometheus:9090|' | kubectl replace -f -
```

## Confirm

`python verifiers/verify.py scenarios/grafana-datasource-089` passes.
