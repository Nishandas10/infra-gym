# Reference solution: net-packet-loss-052

**Heavy packet loss on a service's network interface**

**Root cause:** A Chaos Mesh NetworkChaos experiment drops 60% of packets leaving the product-catalog pod. TCP retransmits turn that into multi-second latency and occasional timeouts. Now and then frontend's gRPC client to product-catalog stays stuck on a dead connection after the experiment is gone, so browse keeps timing out until frontend is restarted; the reference fix restarts it after deleting the experiment.

## How to find it

1. Jaeger: time spent waiting on product-catalog calls, not inside them.
2. `kubectl get pods`: nothing is crashing.
3. `kubectl get networkchaos -A`: `catalog-packet-loss`.

## Fix

```bash
kubectl delete networkchaos.chaos-mesh.org catalog-packet-loss
kubectl rollout restart deployment/frontend
kubectl rollout status deployment/frontend --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/net-packet-loss-052` passes.
