# Reference solution: pg-lock-held-081

**A stuck maintenance job holds an exclusive table lock**

**Root cause:** A `catalog-maintenance` job opened a transaction and took an ACCESS EXCLUSIVE lock on `catalog.products`, then got stuck. Every product query waits behind the lock.

## How to find it

1. product-catalog: queries hang (no error, just timeouts).
2. `psql -c "select pid, state, query, wait_event_type from pg_stat_activity"`: product queries waiting on a Lock; one session idle in transaction holding it.
3. `kubectl get pods`: `catalog-maintenance` is the lock holder. Stop it (or `pg_terminate_backend`).

## Fix

```bash
kubectl delete deployment catalog-maintenance
```

## Confirm

`python verifiers/verify.py scenarios/pg-lock-held-081` passes.
