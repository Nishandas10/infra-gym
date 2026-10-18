# Reference solution: serviceaccount-deleted-122

**The shop's ServiceAccount was deleted; a restarted cart pod can never be created again**

**Root cause:** The ServiceAccount `my-shop`, which every shop Deployment runs its pods as, was deleted. Pods that were already running keep running, but the API server rejects every new pod that names a ServiceAccount that does not exist. The cart pod was replaced afterwards, so its ReplicaSet keeps failing with `error looking up service account default/my-shop` and the cart has no pod at all; adding to cart and checkout fail.

## How to find it

1. `kubectl get pods -l opentelemetry.io/name=cart`: no pod.
2. `kubectl describe rs -l opentelemetry.io/name=cart` / `kubectl get events`: FailedCreate, `pods "cart-..." is forbidden: error looking up service account default/my-shop: serviceaccount "my-shop" not found`.
3. `kubectl get serviceaccounts`: no `my-shop`; every shop Deployment has `serviceAccountName: my-shop`.

## Fix

Recreate the ServiceAccount `my-shop`, then restart cart (`kubectl rollout restart deployment/cart`). The ReplicaSet retries the failed pod creation with an exponential backoff, which after a long outage reaches about 16 minutes, so without the restart cart can stay down long after the ServiceAccount is back. Pointing the cart Deployment at another ServiceAccount (e.g. `default`) also brings cart back but leaves every other shop workload unable to restart.

```bash
kubectl create serviceaccount my-shop
kubectl rollout restart deployment/cart
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/serviceaccount-deleted-122` passes.
