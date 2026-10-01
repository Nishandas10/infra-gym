# Reference solution: wl-image-pull-011

**Mistyped image tag -> ImagePullBackOff**

**Root cause:** The currency Deployment's image tag was mistyped (`3.1.0-curency`). The registry has no such image, so the new pod is stuck in ImagePullBackOff, and the Recreate strategy removed the old pod first.

## How to find it

1. `kubectl get pods`: currency is `ErrImagePull` / `ImagePullBackOff`.
2. `kubectl describe pod -l opentelemetry.io/name=currency`: events say the image tag was not found.
3. `kubectl get deploy currency -o jsonpath='{.spec.template.spec.containers[0].image}'` shows the typo.

## Fix

```bash
kubectl set image deployment/currency currency=ghcr.io/open-telemetry/demo:3.1.0-currency
kubectl rollout status deployment/currency --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/wl-image-pull-011` passes.
