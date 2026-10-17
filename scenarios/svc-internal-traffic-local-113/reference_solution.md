# Reference solution: svc-internal-traffic-local-113

**Service set to internalTrafficPolicy Local; callers on other nodes cannot reach its single pod**

**Root cause:** The currency Service was set to `internalTrafficPolicy: Local`, so kube-proxy sends in-cluster traffic only to a currency pod on the caller's own node and drops it otherwise. Currency has one replica, and frontend and checkout run on another node, so their calls time out while the currency pod, its endpoint and its logs all look healthy.

## How to find it

1. `kubectl logs deploy/checkout`: currency calls time out or are unavailable.
2. `kubectl get pods -o wide`: currency runs on a different node than frontend and checkout.
3. `kubectl get endpointslices -l kubernetes.io/service-name=currency`: one ready endpoint.
4. `kubectl get svc currency -o yaml`: `internalTrafficPolicy: Local`; every other Service uses `Cluster`.
5. A test pod on the currency pod's node connects to currency:8080; one on the other worker node times out.

## Fix

Set `internalTrafficPolicy` back to `Cluster` (removing the field has the same effect). Moving frontend or checkout onto the currency pod's node, or scaling currency up, only hides the fault for the nodes that happen to have a currency pod.

```bash
kubectl patch service currency --type=json -p '[{"op":"replace","path":"/spec/internalTrafficPolicy","value":"Cluster"}]'
```

## Confirm

`python verifiers/verify.py scenarios/svc-internal-traffic-local-113` passes.
