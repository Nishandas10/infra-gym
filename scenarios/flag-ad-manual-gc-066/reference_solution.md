# Reference solution: flag-ad-manual-gc-066

**Ad service triggers full garbage collections (adManualGc)**

**Root cause:** The `adManualGc` flag makes the ad service fill its heap with throwaway objects and force full `System.gc()` runs, causing long stop-the-world pauses. The JVM can stay stuck in garbage collection after the flag is turned off, so the service also needs a restart.

## How to find it

1. Jaeger: GetAds spans have long gaps inside the service.
2. JVM metrics (Grafana): GC pause time spikes; heap usage pinned near its maximum.
3. ad logs: `Triggering a manual garbage collection` / `The artificially triggered GCs took ... ms`.
4. Feature Flags UI: `adManualGc` is on.

## Fix

```bash
python injectors/toggle_flag.py adManualGc --off
kubectl rollout restart deployment/ad
kubectl rollout status deployment/ad --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/flag-ad-manual-gc-066` passes.
