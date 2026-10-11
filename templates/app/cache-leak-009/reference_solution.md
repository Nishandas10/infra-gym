# Reference solution: cache-leak-009

**Root cause:** the `recommendationCacheFailure` flag turns on a broken "cache"
in the recommendation service. Every cache miss appends the product list to
itself, so memory and response time grow over time until the container is
OOMKilled at its 500Mi limit. After the restart the cycle begins again.

1. Watch it grow:
   `kubectl get pods -l opentelemetry.io/name=recommendation -w` shows restarts;
   `kubectl describe pod -l opentelemetry.io/name=recommendation` shows
   `Last State: Terminated, Reason: OOMKilled`.
2. Latency: `/api/recommendations` gets slower with every minute. In Jaeger the
   `get_product_list` span grows, with `app.cache_hit` attributes on it.
3. Grafana (demo dashboard): the recommendation container's memory climbs in a
   sawtooth.
4. Feature Flags UI: `recommendationCacheFailure` is on.
5. Fix: turn the flag off, then restart the service. The memory already
   leaked stays in the running process until it restarts.
   ```
   python injectors/toggle_flag.py recommendationCacheFailure --off
   kubectl rollout restart deployment/recommendation
   kubectl rollout status deployment/recommendation
   ```
6. Confirm recommendations stay fast and the pod stops restarting.

A shallow fix, restarting the pod without turning the flag off, only resets
the sawtooth. The verifier's 10-minute stability check catches that.
