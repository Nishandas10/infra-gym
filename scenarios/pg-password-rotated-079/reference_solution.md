# Reference solution: pg-password-rotated-079

**Database password rotated without updating the clients**

**Root cause:** `astronomy_user`'s password was rotated in Postgres and existing sessions were terminated, but product-catalog and accounting still use the old password from their configuration. Every reconnect fails authentication.

## How to find it

1. product-catalog logs: `password authentication failed for user "astronomy_user"`.
2. The database is up; other roles can log in.
3. Either roll the password back or update the clients' secret. The reference fix restores the password the apps are configured with.

## Fix

```bash
kubectl exec deploy/astronomy-db -- psql -U postgres -c "ALTER ROLE astronomy_user PASSWORD 'astronomy_password'"
```

## Confirm

`python verifiers/verify.py scenarios/pg-password-rotated-079` passes.
