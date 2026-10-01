# Reference solution: pod-security-restricted-049

**Namespace switched to the 'restricted' Pod Security Standard**

**Root cause:** The namespace was labelled `pod-security.kubernetes.io/enforce=restricted`. Existing pods keep running, but any recreated pod that does not meet the restricted profile is rejected at admission.

## How to find it

1. `kubectl get pods`: no image-provider pod.
2. `kubectl describe rs -l opentelemetry.io/name=image-provider`: `violates PodSecurity "restricted:latest"`.
3. `kubectl get namespace default --show-labels`.

## Fix

```bash
kubectl label namespace default pod-security.kubernetes.io/enforce-
kubectl rollout restart deployment/image-provider
kubectl rollout status deployment/image-provider --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/pod-security-restricted-049` passes.
