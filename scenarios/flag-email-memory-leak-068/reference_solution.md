# Reference solution: flag-email-memory-leak-068

**Email service leaks memory until it is OOMKilled (emailMemoryLeak)**

**Root cause:** The `emailMemoryLeak` flag makes the email service keep a growing copy of data for every email, so its memory climbs until it is OOMKilled at its 100Mi limit, over and over.

## How to find it

1. `kubectl describe pod -l opentelemetry.io/name=email`: `Last State: OOMKilled`, restart count rising.
2. Memory graph: sawtooth.
3. Feature Flags UI: `emailMemoryLeak` is on. Turn it off, then restart to drop the leaked memory.

## Fix

```bash
python injectors/toggle_flag.py emailMemoryLeak --off
kubectl rollout restart deployment/email
kubectl rollout status deployment/email --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/flag-email-memory-leak-068` passes.
