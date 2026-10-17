# Reference solution: rollout-wrong-artifact-115

**A payment release shipped another service's image; the new pod starts and crashes**

**Root cause:** The payment 3.1.1 release points the Deployment at `ghcr.io/open-telemetry/demo:3.1.0-quote`, the quote service's image. It pulls and starts, then exits, because it is a different program with a different configuration. With one replica and no readiness probe the rollout replaced the working pod, so every payment fails.

## How to find it

1. `kubectl get pods`: the payment pod is in Error / CrashLoopBackOff.
2. `kubectl logs deploy/payment --previous`: startup output of the quote service, not payment's Node.js logs.
3. `kubectl get deploy payment -o jsonpath='{..image}'`: demo:3.1.0-quote, unlike every other service's demo:3.1.0-<own name>.
4. `kubectl rollout history deployment/payment`: the latest revision is the 3.1.1 hotfix.

## Fix

Roll payment back to the previous revision, or set its image back to ghcr.io/open-telemetry/demo:3.1.0-payment.

```bash
kubectl rollout undo deployment/payment
kubectl rollout status deployment/payment --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/rollout-wrong-artifact-115` passes.
