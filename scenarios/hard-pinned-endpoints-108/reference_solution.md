# Reference solution: hard-pinned-endpoints-108

**The quote Service was pinned to a fixed IP during an old incident and never unpinned**

**Root cause:** The quote Service has no selector and a hand-made EndpointSlice (quote-pinned, from incident INC-5521) that points at 10.244.250.17, an IP no pod has any more. shipping's calls to quote time out. Restoring the selector alone is not enough: the pinned slice keeps the dead IP in rotation.

## How a careful SRE finds it

1. shipping logs: requests to http://quote:8080 time out. quote pods are Running and log nothing.
2. `kubectl get endpointslices -l kubernetes.io/service-name=quote` shows quote-pinned with 10.244.250.17, which matches no pod (`kubectl get pods -o wide`).
3. `kubectl get svc quote -o yaml`: no spec.selector, so Kubernetes manages no endpoints for it.
4. Restore the selector from the quote Deployment's labels and delete the pinned EndpointSlice.

## Traps (why this is hard)

- Restarting quote or shipping (changes nothing).
- Restoring the selector but keeping the pinned slice: the dead IP stays in rotation (intermittent).

## Noise in this scenario (not the cause)

- crash-looping quote-cache-warmer (pricing team) logging upstream timeouts

## Fix

```bash
kubectl patch service quote --type=merge -p '{"spec":{"selector":{"opentelemetry.io/name":"quote"}}}'
kubectl delete endpointslice quote-pinned
```

## Confirm

`python verifiers/verify.py scenarios/hard-pinned-endpoints-108` passes.
