# Reference solution: hard-silent-ledger-write-denied-105

**Orders disappear between checkout and the accounting ledger (write permission revoked)**

**Root cause:** astronomy_user lost INSERT on accounting."order". Checkout and Kafka are fine; the accounting consumer fails on every insert, so orders never reach the ledger. Nothing user-facing fails.

## How a careful SRE finds it

1. Every user journey passes; the problem is in the asynchronous path checkout -> Kafka -> accounting -> DB.
2. accounting logs: 'permission denied for table order' on insert.
3. In the DB (`kubectl exec deploy/astronomy-db -- psql -U postgres -d astronomy_db`): `\dp accounting."order"` shows astronomy_user has no INSERT.

## Traps (why this is hard)

- Stopping at 'checkout works' because every user-facing check is green.
- Chasing the S3 export failure or the Pending GPU job (other teams, unrelated).

## Noise in this scenario (not the cause)

- failed nightly S3 export Job
- Pending GPU retraining pod with FailedScheduling events

## Fix

GRANT INSERT on accounting."order" back to astronomy_user, then restart accounting so it reconnects.

```bash
kubectl exec deploy/astronomy-db -- psql -U postgres -d astronomy_db -c 'GRANT INSERT ON accounting."order" TO astronomy_user'
kubectl rollout restart deployment/accounting
kubectl rollout status deployment/accounting --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-silent-ledger-write-denied-105` passes.
