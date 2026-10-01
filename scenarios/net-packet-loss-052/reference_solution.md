# Reference solution: net-packet-loss-052

**Heavy packet loss on a service's network interface**

**Root cause:** A Chaos Mesh NetworkChaos experiment drops 60% of packets leaving the product-catalog pod. TCP retransmits turn that into multi-second latency and occasional timeouts.

## How to find it

1. Jaeger: time spent waiting on product-catalog calls, not inside them.
2. `kubectl get pods`: nothing is crashing.
3. `kubectl get networkchaos -A`: `catalog-packet-loss`.

## Fix

```bash
kubectl delete networkchaos.chaos-mesh.org catalog-packet-loss
```

## Confirm

`python verifiers/verify.py scenarios/net-packet-loss-052` passes.
