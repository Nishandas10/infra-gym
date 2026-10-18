# Reference solution: svc-externalname-redirect-119

**cart Service converted to ExternalName for an unfinished migration; new connections to cart cannot resolve**

**Root cause:** An unfinished migration converted the cart Service to `type: ExternalName` with `externalName: cart.cart-v2.svc.cluster.local`; the namespace cart-v2 does not exist. The change dropped the Service's cluster IP, and the cluster DNS now answers `cart` with a CNAME to a name that does not resolve. Frontend and checkout kept working on their existing gRPC connections until they were redeployed; every new connection fails, so adding to the cart and checkout fail while the cart pod itself is healthy. The deploys are not the cause.

## How to find it

1. `kubectl logs deploy/frontend`: errors calling the cart service (name resolution / UNAVAILABLE).
2. `kubectl get svc cart`: TYPE `ExternalName`, EXTERNAL-IP `cart.cart-v2.svc.cluster.local`, no cluster IP; every other shop Service is `ClusterIP`.
3. `kubectl get ns cart-v2`: NotFound.
4. `kubectl get pods -l opentelemetry.io/name=cart`: Running and Ready; its EndpointSlice still lists the pod.

## Noise in this scenario (not the cause)

- The frontend and checkout deploys look like the trigger; rolling them back or restarting them changes nothing.

## Fix

Change the cart Service back to `type: ClusterIP` and drop `externalName` (Kubernetes assigns a new cluster IP; clients use the name, so that is fine). Deleting the Service and recreating it as ClusterIP with the same selector and port also works. Rolling back or restarting frontend and checkout does not.

```bash
kubectl patch service cart --type merge -p '{"spec":{"type":"ClusterIP","externalName":null}}'
```

## Confirm

`python verifiers/verify.py scenarios/svc-externalname-redirect-119` passes.
