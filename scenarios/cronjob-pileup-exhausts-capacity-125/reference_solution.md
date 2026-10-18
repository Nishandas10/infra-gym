# Reference solution: cronjob-pileup-exhausts-capacity-125

**A report CronJob piles up hung runs until no node has memory left; a restarted recommendation pod cannot fit**

**Root cause:** The data team's report-export CronJob starts 20 pods every minute (450Mi requested each), with `concurrencyPolicy: Allow`, and every run hangs waiting for a lock instead of finishing. Within minutes the runs have reserved nearly all the workers' memory. When the recommendation pod was recreated, no node had room for its request, so it is Pending (Insufficient memory) and the storefront shows no recommendations. More runs keep arriving every minute, so deleting a few pods only helps until the next run.

## How to find it

1. `kubectl get pods -l opentelemetry.io/name=recommendation`: Pending; `kubectl describe pod`: 0/3 nodes are available: Insufficient memory.
2. `kubectl describe nodes`: memory requests at ~98% on every worker.
3. `kubectl get cronjobs,jobs`: report-export, concurrencyPolicy Allow, one Job per minute, none completing.
4. `kubectl logs` of a report-export pod: "waiting for the export lock".

## Fix

Stop the pile-up at its source: suspend the CronJob (or set `concurrencyPolicy: Forbid` and an `activeDeadlineSeconds`, or delete it), then delete its hung Jobs so their memory is released. Deleting pods or Jobs alone is undone by the next run within a minute; scaling recommendation or lowering its request does not address the cause.

```bash
kubectl patch cronjob report-export --type merge -p '{"spec":{"suspend":true}}'
kubectl delete jobs -l app.kubernetes.io/name=report-export --wait=false
kubectl rollout status deployment/recommendation --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/cronjob-pileup-exhausts-capacity-125` passes.
