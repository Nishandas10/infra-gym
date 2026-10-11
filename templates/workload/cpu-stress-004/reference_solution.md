# Reference solution: cpu-stress-004

**Root cause:** a Chaos Mesh `StressChaos` experiment runs two `stress-ng` CPU
workers inside the frontend container, which burn about two cores. The
frontend has no CPU limit, so the site stays mostly responsive; the damage is
wasted CPU and noisy-neighbour pressure on the node.

1. Confirm the symptom: `kubectl get --raw /api/v1/nodes/<node>/proxy/stats/summary`
   (or Grafana) shows the frontend container at about 2 cores while request rates
   are flat.
2. Find the culprit processes:
   `kubectl exec deploy/frontend -- ps aux` (if `ps` exists) shows `stress-ng`
   processes next to `node`.
3. Nothing in the frontend's own deployment changed:
   `kubectl rollout history deployment/frontend`.
4. Look for an active experiment:
   ```
   kubectl get stresschaos -A
   ```
5. Remove it:
   ```
   kubectl delete stresschaos cpu-stress-004
   ```
6. Confirm CPU drops back to near zero.
