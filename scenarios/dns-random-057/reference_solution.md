# Reference solution: dns-random-057

**DNS returns random addresses for one name**

**Root cause:** A DNSChaos experiment makes recommendation's DNS lookups of `product-catalog` return random IP addresses. The lookups succeed, so there is no DNS error, but the connections go nowhere.

## How to find it

1. recommendation logs: connection failures / timeouts to odd IP addresses for product-catalog.
2. `nslookup product-catalog` from another pod returns the correct ClusterIP.
3. `kubectl get dnschaos -A`: `catalog-dns-random`.

## Fix

```bash
kubectl delete dnschaos.chaos-mesh.org catalog-dns-random
```

## Confirm

`python verifiers/verify.py scenarios/dns-random-057` passes.
