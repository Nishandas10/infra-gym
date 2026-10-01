# Reference solution: valkey-maxmemory-075

**Valkey memory cap reached with 'noeviction' -> writes rejected**

**Root cause:** Valkey's `maxmemory` was set to 256kb, below the memory it already uses, while `maxmemory-policy` is `noeviction`. Reads work; every write fails with `OOM command not allowed when used memory > 'maxmemory'`.

## How to find it

1. cart logs: `OOM command not allowed` on writes.
2. `kubectl exec deploy/valkey-cart -- valkey-cli INFO memory`: used_memory > maxmemory, policy noeviction.
3. Raise or remove the cap (or allow eviction).

## Fix

```bash
kubectl exec deploy/valkey-cart -- valkey-cli CONFIG SET maxmemory 0
```

## Confirm

`python verifiers/verify.py scenarios/valkey-maxmemory-075` passes.
