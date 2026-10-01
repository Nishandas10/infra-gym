# Reference solution: kube-proxy-stopped-051

**kube-proxy removed; Service rules go stale when a pod moves**

**Root cause:** kube-proxy (which programs Service IPs into node network rules) was removed by a nodeSelector no node matches. The old rules stay in place, so nothing breaks until an endpoint changes. When payment got a new pod IP, the `payment` Service kept sending traffic to the old IP.

## How to find it

1. Endpoints for `payment` show the new pod IP, yet checkout cannot connect.
2. `kubectl -n kube-system get pods -l k8s-app=kube-proxy`: none running.
3. `kubectl -n kube-system get ds kube-proxy -o yaml`: nodeSelector `proxy-tier=disabled`.

## Fix

```bash
kubectl -n kube-system patch daemonset kube-proxy --type=json -p '[{"op":"remove","path":"/spec/template/spec/nodeSelector/proxy-tier"}]'
kubectl -n kube-system rollout status daemonset/kube-proxy --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/kube-proxy-stopped-051` passes.
