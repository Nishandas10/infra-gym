# Reference solution: hard-mutating-policy-rewrites-pods-131

**Checkout calls the wrong payment port although its Deployment is correct**

**Root cause:** A MutatingAdmissionPolicy named platform-pod-defaults (with a binding of the same name) changes every checkout pod at creation, setting PAYMENT_ADDR to payment:8081. The payment Service listens on 8080, so every checkout fails. The checkout Deployment, its ReplicaSet and its rollout history are all correct; only the running pods differ. Patching the Deployment or restarting checkout changes nothing, because each new pod is rewritten again. The policy is cluster-scoped.

## How a careful SRE finds it

1. checkout logs: payment calls fail with connection refused on payment:8081.
2. `kubectl get deploy checkout -o yaml` shows PAYMENT_ADDR=payment:8080; `kubectl get pod <checkout pod> -o yaml` shows payment:8081.
3. `kubectl get mutatingadmissionpolicies,mutatingadmissionpolicybindings` lists platform-pod-defaults, which targets checkout pods.

## Traps (why this is hard)

- Setting PAYMENT_ADDR on the Deployment again, or restarting checkout: each new pod is rewritten.
- Restarting checkout right after deleting the policy: the API server can still apply it for a few seconds; check the new pod's env and restart again if needed.

## Noise in this scenario (not the cause)

- The payment Service and pods are healthy; port 8080 works from any other client.

## Fix

Delete the MutatingAdmissionPolicy platform-pod-defaults and its binding, wait a few seconds for the API server to drop it, then restart checkout so its pods are created with the Deployment's configuration.

```bash
kubectl delete mutatingadmissionpolicybinding platform-pod-defaults
kubectl delete mutatingadmissionpolicy platform-pod-defaults
sleep 15
kubectl rollout restart deployment/checkout
kubectl rollout status deployment/checkout --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-mutating-policy-rewrites-pods-131` passes.
