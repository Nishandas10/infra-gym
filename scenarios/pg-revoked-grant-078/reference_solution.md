# Reference solution: pg-revoked-grant-078

**Database role lost SELECT on the table the service reads**

**Root cause:** The audit revoked `SELECT` on `catalog.products` from `astronomy_user`, the role product-catalog connects as. Every query fails with `permission denied for table products`.

## How to find it

1. product-catalog logs: `permission denied for table products`.
2. `psql ... -c '\dp catalog.products'`: astronomy_user has no SELECT.
3. Re-grant the privilege.

## Fix

```bash
kubectl exec deploy/astronomy-db -- psql -U postgres -d astronomy_db -c 'GRANT SELECT ON catalog.products TO astronomy_user'
```

## Confirm

`python verifiers/verify.py scenarios/pg-revoked-grant-078` passes.
