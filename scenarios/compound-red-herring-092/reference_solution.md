# Reference solution: compound-red-herring-092

**A loud but irrelevant failing pod next to the real, quieter fault**

**Root cause:** The crash-looping `legacy-report-generator` is a red herring: it is broken but nothing depends on it. The orders fail because the quote Deployment was scaled to zero, so shipping cannot get quotes.

## How to find it

1. Start from the failing request: checkout logs point at shipping, and shipping logs point at quote.
2. `kubectl get deploy quote`: 0 replicas.
3. The report generator's logs mention a database nothing else uses.

## Fix

```bash
kubectl scale deployment quote --replicas=1
kubectl rollout status deployment/quote --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/compound-red-herring-092` passes.
