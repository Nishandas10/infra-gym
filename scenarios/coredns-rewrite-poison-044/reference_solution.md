# Reference solution: coredns-rewrite-poison-044

**CoreDNS rewrite rule sends one service's name to another**

**Root cause:** Someone added `rewrite name payment.default.svc.cluster.local shipping.default.svc.cluster.local` to the CoreDNS Corefile. Lookups of `payment` return the shipping Service's IP, so checkout's gRPC calls reach an HTTP server and fail.

## How to find it

1. `kubectl logs deploy/checkout`: protocol / unavailable errors calling payment.
2. `kubectl run -it --rm dnstest --image=busybox --restart=Never -- nslookup payment`: returns the IP of the `shipping` Service (compare `kubectl get svc`).
3. `kubectl -n kube-system get configmap coredns -o yaml`: the rewrite rule.

## Fix

```bash
kubectl -n kube-system get configmap coredns -o yaml | sed '/rewrite name payment.default/d' | kubectl apply -f -
kubectl -n kube-system rollout restart deployment/coredns
kubectl -n kube-system rollout status deployment/coredns --timeout=300s
kubectl rollout restart deployment/checkout
kubectl rollout status deployment/checkout --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/coredns-rewrite-poison-044` passes.
