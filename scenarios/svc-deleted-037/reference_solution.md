# Reference solution: svc-deleted-037

**Service object deleted**

**Root cause:** The `email` Service was deleted, so the name `email` no longer resolves. Checkout only logs the failed send, so orders keep succeeding. Helm still has the Service in its release, so re-syncing the release recreates it.

## How to find it

1. `kubectl logs deploy/checkout`: `lookup email ... no such host` when sending confirmations.
2. `kubectl get svc email`: NotFound, while the email pod is Running.
3. Recreate it from the source of truth (`helm upgrade` via `scripts/reset_world.sh`), not by hand, so Helm keeps ownership.

## Fix

```bash
bash scripts/reset_world.sh
```

## Confirm

`python verifiers/verify.py scenarios/svc-deleted-037` passes.
