# Reference solution: pod-failure-055

**Pod stays 'Running' but its process has been replaced by a pause container**

**Root cause:** A PodChaos `pod-failure` experiment swapped the shipping container's image for a `pause` image, so the pod exists and looks alive but nothing is serving.

## How to find it

1. `kubectl get pods`: shipping Running, but connections to it fail.
2. `kubectl get pod -l opentelemetry.io/name=shipping -o jsonpath='{.items[0].spec.containers[0].image}'`: a pause image, not the shipping image.
3. `kubectl get podchaos -A`: `shipping-pod-failure`.

## Fix

```bash
kubectl delete podchaos.chaos-mesh.org shipping-pod-failure
```

## Confirm

`python verifiers/verify.py scenarios/pod-failure-055` passes.
