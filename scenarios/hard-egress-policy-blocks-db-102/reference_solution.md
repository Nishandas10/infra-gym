# Reference solution: hard-egress-policy-blocks-db-102

**A security-hardening egress policy forgets the database port; everything points at the database**

**Root cause:** NetworkPolicy product-catalog-egress-hardening allows egress only to DNS and a list of service ports that omits PostgreSQL (5432), so product-catalog cannot reach astronomy-db. The database is healthy; the failed backup job and the crash-looping search indexer are unrelated noise.

## How a careful SRE finds it

1. product-catalog logs (or crash loop): timeouts connecting to astronomy-db:5432.
2. astronomy-db itself is healthy: `kubectl exec deploy/astronomy-db -- psql -U postgres -c 'select 1'` works, and connections from other pods succeed. So the path, not the database, is broken.
3. A timeout (not 'connection refused' or an auth error) from one client suggests filtering.
4. `kubectl get networkpolicy` shows product-catalog-egress-hardening; its egress ports omit 5432.
5. Add 5432 to the policy (or remove the policy), then restart product-catalog.

## Traps (why this is hard)

- Chasing the backup job's password error or the indexer's timeouts (other teams, unrelated).
- Restarting or reconfiguring the database (changes nothing).
- Deleting other teams' workloads to 'clean up' (counts as a distractor touch).

## Noise in this scenario (not the cause)

- failed backup Job with a password error
- crash-looping search indexer logging DB timeouts

## Fix

```bash
kubectl patch networkpolicy product-catalog-egress-hardening --type=json -p '[{"op":"add","path":"/spec/egress/1/ports/-","value":{"protocol":"TCP","port":5432}}]'
kubectl rollout restart deployment/product-catalog
kubectl rollout status deployment/product-catalog --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-egress-policy-blocks-db-102` passes.
