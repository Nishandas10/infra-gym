# Reference solution: prometheus-sa-token-not-mounted-123

**A hardening change stopped mounting Prometheus's service account token; its Kubernetes scrape targets vanish**

**Root cause:** A pod hardening change set `automountServiceAccountToken: false` on several Deployments, Prometheus among them. Prometheus discovers its kubernetes-pods targets and scrapes the nodes' cadvisor through the Kubernetes API with the pod's service account token and CA certificate. Without the mounted token those scrape pools fail ("unable to read CA cert"), so every container and pod-annotation metric disappears. Application metrics still arrive because the collector pushes them over OTLP. Prometheus itself stays Running and Ready.

## How to find it

1. `kubectl logs deploy/prometheus`: `error creating new scrape pool ... unable to read CA cert` for the kubernetes-* jobs.
2. Prometheus `up{job="kubernetes-nodes-cadvisor"}` and `up{job="kubernetes-pods"}` return nothing; OTLP application metrics are still current.
3. `kubectl get deploy prometheus -o yaml`: `automountServiceAccountToken: false` in the pod template; the pod has no /var/run/secrets/kubernetes.io/serviceaccount volume.

## Noise in this scenario (not the cause)

- quote and currency got the same `automountServiceAccountToken: false`; they never call the Kubernetes API and are unaffected.

## Fix

Remove `automountServiceAccountToken: false` from the Prometheus Deployment's pod template (or set it to true); the rollout gives the new pod its token and the Kubernetes scrape jobs come back within about a minute. quote and currency do not need to change.

```bash
kubectl patch deployment prometheus --type json -p '[{"op":"remove","path":"/spec/template/spec/automountServiceAccountToken"}]'
kubectl rollout status deployment/prometheus --timeout=240s
```

## Confirm

`python verifiers/verify.py scenarios/prometheus-sa-token-not-mounted-123` passes.
