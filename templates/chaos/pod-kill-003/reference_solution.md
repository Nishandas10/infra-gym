# Reference solution: pod-kill-003

**Root cause:** a Chaos Mesh `Schedule` kills the checkout pod every 45 seconds.
Each replacement takes a few seconds to start, so orders placed in that window
fail. A retry lands on the new pod and works, which is why it looks intermittent.

1. `kubectl get pods -l opentelemetry.io/name=checkout -w`: the pod name
   changes about every 45 s, and its AGE never gets past a minute.
2. `kubectl get events --sort-by=.lastTimestamp | grep checkout`: repeated
   `Killing` events with no OOM or probe failure behind them. Something external
   deletes the pod.
3. Look for a scheduled experiment:
   ```
   kubectl get schedules.chaos-mesh.org,podchaos -A
   ```
4. Remove it:
   ```
   kubectl delete schedule.chaos-mesh.org pod-kill-003
   ```
5. Confirm the pod stays up for more than 90 s and orders succeed.
