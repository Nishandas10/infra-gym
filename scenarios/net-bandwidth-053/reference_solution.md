# Reference solution: net-bandwidth-053

**Bandwidth throttled to a trickle on the image server**

**Root cause:** A NetworkChaos bandwidth experiment limits the image server to 2 kilobytes per second. Small API responses are barely affected, but images of tens of kilobytes take many seconds to transfer.

## How to find it

1. Only large responses are slow; latency grows with response size.
2. `kubectl get networkchaos -A`: `images-bandwidth`.

## Fix

```bash
kubectl delete networkchaos.chaos-mesh.org images-bandwidth
```

## Confirm

`python verifiers/verify.py scenarios/net-bandwidth-053` passes.
