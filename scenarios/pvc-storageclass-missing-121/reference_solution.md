# Reference solution: pvc-storageclass-missing-121

**valkey-cart moved onto a PVC with a StorageClass this cluster does not have; the cart store never starts**

**Root cause:** valkey-cart (the cart's Redis-compatible store) was moved onto a PersistentVolumeClaim `valkey-data` with `storageClassName: premium-rwo`, a class name copied from another cloud. This cluster only has the `standard` class, so the claim is never provisioned (ProvisioningFailed: storageclass "premium-rwo" not found), the new valkey-cart pod is Pending (unbound PersistentVolumeClaim), and with the Recreate strategy the old pod is already gone: every cart call times out.

## How to find it

1. `kubectl get pods -l opentelemetry.io/name=valkey-cart`: Pending; `kubectl describe pod`: pod has unbound immediate PersistentVolumeClaims.
2. `kubectl get pvc valkey-data`: Pending, STORAGECLASS premium-rwo.
3. `kubectl describe pvc valkey-data`: ProvisioningFailed, storageclass.storage.k8s.io "premium-rwo" not found.
4. `kubectl get storageclass`: only `standard` (default).

## Fix

A PVC's storageClassName cannot be changed: delete the claim (and the Pending pod that holds it) and recreate it without a class (or with `standard`). Removing the volume from valkey-cart (back to its old ephemeral storage) also works. Creating a StorageClass is not possible with the on-call permissions here.

```bash
kubectl delete pvc valkey-data --wait=false
kubectl delete pod -l opentelemetry.io/name=valkey-cart --wait=false
sleep 10
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: valkey-data, namespace: default}
spec:
  accessModes: [ReadWriteOnce]
  resources: {requests: {storage: 1Gi}}
EOF
kubectl rollout status deployment/valkey-cart --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/pvc-storageclass-missing-121` passes.
