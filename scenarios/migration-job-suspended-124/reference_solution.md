# Reference solution: migration-job-suspended-124

**A product-catalog release waits for a schema migration whose Job was created suspended**

**Root cause:** product-catalog 3.2.0 (rolled out with the Recreate strategy, so the old pod is gone) has a new init container that waits until schema version 42 is recorded in catalog.schema_migrations. The migration that records it is the Job `catalog-migrate-42`, which was created with `spec.suspend: true` and never started. The new pod stays at Init:1/2, product-catalog has no ready pod, and every product page fails. Unsuspending the Job runs the migration (about 3 s); the init container then passes and product-catalog starts.

## How to find it

1. `kubectl get pods -l opentelemetry.io/name=product-catalog`: Init:1/2; `kubectl logs <pod> -c wait-for-schema`: "waiting for schema version 42".
2. `kubectl get jobs`: catalog-migrate-42 is Suspended with 0/1 completions; its annotation names the 3.2.0 release.
3. `kubectl rollout history deployment/product-catalog`: 3.2.0 "product search index, needs schema 42".
4. `select * from catalog.schema_migrations`: versions 40 and 41 only.

## Fix

Unsuspend the migration Job (`kubectl patch job catalog-migrate-42 -p '{"spec":{"suspend":false}}'`); once it completes, the waiting init container passes and product-catalog starts. Running the same migration SQL by hand is also acceptable. Rolling back the release or removing its init container restores the pages but leaves schema 42 unapplied, and the release has to stay.

```bash
kubectl patch job catalog-migrate-42 --type merge -p '{"spec":{"suspend":false}}'
kubectl wait --for=condition=complete job/catalog-migrate-42 --timeout=120s
kubectl rollout status deployment/product-catalog --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/migration-job-suspended-124` passes.
