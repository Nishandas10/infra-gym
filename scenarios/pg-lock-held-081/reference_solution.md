# Reference solution: pg-lock-held-081

**A stuck maintenance job holds an exclusive table lock**

**Root cause:** A `catalog-maintenance` job opened a transaction, took an ACCESS EXCLUSIVE lock on `catalog.products` and then sat in `pg_sleep`. Every product query waits behind the lock until the role's 3 s lock_timeout cancels it, so every product page fails. The job retries in a loop, so ending only its database session gets the lock taken again within seconds; deleting only the job leaves its session running (Postgres does not notice the vanished client while the statement runs), still holding the lock. Both are needed: stop the job, then end its session.

## How to find it

1. `kubectl logs deploy/product-catalog`: queries fail with "canceling statement due to lock timeout".
2. `psql -c "select pid, state, query, wait_event_type from pg_stat_activity"`: product queries waiting on a Lock; one postgres session running `BEGIN; LOCK TABLE catalog.products ...; SELECT pg_sleep(86400)`.
3. `kubectl get pods`: `catalog-maintenance` runs the psql client of that session.

## Noise in this scenario (not the cause)

- The lock_timeout on astronomy_user only turns the hang into fast errors; removing it makes pages hang instead.

## Fix

Delete (or scale to 0) the catalog-maintenance Deployment, then end its leftover database session with `pg_terminate_backend(<pid>)` (the pid from pg_stat_activity). Either step alone leaves the lock in place: the job takes it again, or the orphaned session keeps it.

```bash
kubectl delete deployment catalog-maintenance --wait=true
kubectl exec deploy/astronomy-db -- psql -U postgres -d astronomy_db -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%LOCK TABLE catalog.products%' AND pid <> pg_backend_pid()"
```

## Confirm

`python verifiers/verify.py scenarios/pg-lock-held-081` passes.
