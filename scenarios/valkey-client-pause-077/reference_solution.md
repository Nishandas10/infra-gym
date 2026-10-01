# Reference solution: valkey-client-pause-077

**Valkey clients paused -> writes hang**

**Root cause:** A `CLIENT PAUSE ... WRITE` was issued on valkey-cart (typically left over from a failover or maintenance script), so every write command blocks while reads continue.

## How to find it

1. cart logs: timeouts on writes only.
2. `kubectl exec deploy/valkey-cart -- valkey-cli INFO clients`: clients blocked; `CLIENT LIST` shows paused writes.
3. `CLIENT UNPAUSE` releases them.

## Fix

```bash
kubectl exec deploy/valkey-cart -- valkey-cli CLIENT UNPAUSE
```

## Confirm

`python verifiers/verify.py scenarios/valkey-client-pause-077` passes.
