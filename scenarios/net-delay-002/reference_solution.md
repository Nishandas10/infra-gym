# Reference solution: net-delay-002

**Root cause:** a Chaos Mesh `NetworkChaos` experiment adds about 3 s of latency to
every packet the recommendation pod sends.

1. Reproduce: `/api/recommendations` takes about 6 s (both the request to
   product-catalog and the reply to the frontend are delayed); other APIs are fast.
2. Jaeger, service `frontend`, operation for recommendations: the time is spent
   between spans (on the network), not inside the service code.
3. `kubectl get pods`: nothing is crashing. `kubectl logs deploy/recommendation`
   is clean.
4. Look for an active fault experiment:
   ```
   kubectl get networkchaos -A
   ```
5. Remove it:
   ```
   kubectl delete networkchaos net-delay-002
   ```
6. Confirm recommendations respond quickly again.

In a real incident step 5 is "roll back the network policy / sidecar / tc
change that added the delay". Removing the injected fault stands in for that.
