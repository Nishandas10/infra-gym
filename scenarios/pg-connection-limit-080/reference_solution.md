# Reference solution: pg-connection-limit-080

**Role connection limit set to zero**

**Root cause:** `astronomy_user` was given `CONNECTION LIMIT 0` (an attempt to drain the role before maintenance) and its sessions were terminated. Reconnects are rejected with `too many connections for role`.

## How to find it

1. product-catalog logs: `too many connections for role "astronomy_user"`.
2. `psql -c "select rolname, rolconnlimit from pg_roles"`: connlimit 0.
3. Set it back to -1 (unlimited).

## Fix

```bash
kubectl exec deploy/astronomy-db -- psql -U postgres -c 'ALTER ROLE astronomy_user CONNECTION LIMIT -1'
```

## Confirm

`python verifiers/verify.py scenarios/pg-connection-limit-080` passes.
