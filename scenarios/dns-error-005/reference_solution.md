# Reference solution: dns-error-005

**Root cause:** a Chaos Mesh `DNSChaos` experiment makes DNS lookups of
`valkey-cart` fail, but only from the cart pod. When the valkey pod was
rescheduled, cart's connection dropped and it could not resolve the name again.

1. Reproduce: adding to cart fails; orders fail too (checkout reads the cart).
2. `kubectl get pods`: valkey-cart and cart are both Running.
3. `kubectl logs deploy/cart --tail=50`: connection errors to `valkey-cart`
   mentioning name resolution / `No such host`.
4. Other pods can resolve it, so it is not a cluster-wide DNS outage:
   `kubectl run -it --rm dnstest --image=busybox --restart=Never -- nslookup valkey-cart`
   works; CoreDNS is healthy (`kubectl -n kube-system get pods -l k8s-app=kube-dns`).
5. `kubectl exec deploy/cart -- cat /etc/resolv.conf`: the nameserver is not
   the cluster DNS, so something rewrote it. Look for experiments:
   ```
   kubectl get dnschaos -A
   ```
6. Remove it:
   ```
   kubectl delete dnschaos dns-error-005
   ```
7. Cart reconnects within seconds; confirm adding to cart and ordering work.

Note: the Playbook targets checkout -> payment. Chaos Mesh's DNSChaos needs a
shell inside the target container, and checkout's image is distroless, so this
scenario uses cart -> valkey-cart. The skill being tested is the same.
