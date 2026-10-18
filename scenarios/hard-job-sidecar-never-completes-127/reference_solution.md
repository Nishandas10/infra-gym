# Reference solution: hard-job-sidecar-never-completes-127

**An accounting release waits for a migration Job that never completes because its log-shipper sidecar never exits**

**Root cause:** Accounting 3.2.0 (Recreate strategy, so the old pod is gone) adds an init container that polls the Kubernetes API until Job `ledger-migrate-7` is Complete. The Job's `migrate` container did its work in seconds ("ledger migration 7 applied") and exited 0, but the pod also runs a `log-shipper` as a regular container that loops forever. A pod completes only when all its regular containers have exited, so the Job stays Running at 0/1 completions, the new accounting pod never leaves initialization, the orders consumer group has no members, and orders pile up in Kafka unrecorded while checkout keeps working.

## How a careful SRE finds it

1. `kubectl get pods -l opentelemetry.io/name=accounting`: Init:1/2; `kubectl logs <pod> -c wait-for-ledger-migration`: "waiting for job ledger-migrate-7 to complete".
2. `kubectl get job ledger-migrate-7`: Running, 0/1 completions for minutes; its pod is 1/2 Ready, `migrate` Terminated (Completed) and `log-shipper` still Running.
3. `kubectl logs job/ledger-migrate-7 -c migrate`: "ledger migration 7 applied".
4. Kafka: consumer group accounting has no active members and a growing lag.

## Traps (why this is hard)

- The migration itself already succeeded ("ledger migration 7 applied"), so the Job looks done at a glance.
- Checkout and every user journey stay green; only the ledger, Kafka lag and the accounting pod show it.
- Deleting the stuck Job (the reflex for a stuck Job) leaves the init container waiting for a Job that no longer exists.

## Fix

Make the Job complete. Either recreate it with the log-shipper as a native sidecar (an init container with `restartPolicy: Always`, which Kubernetes stops once the main container exits), or stop the running log-shipper (`kubectl exec job/ledger-migrate-7 -c log-shipper -- kill 1`; it exits 0 on SIGTERM). Once the Job is Complete the init container passes, accounting starts and drains the backlog. Deleting the Job without recreating it leaves accounting waiting forever; removing the init container from the release also restores the ledger but skips the release's migration gate.

```bash
kubectl delete job ledger-migrate-7 --wait=true
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata: {name: ledger-migrate-7, namespace: default, labels: {app.kubernetes.io/name: ledger-migrate}}
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      initContainers:
      - name: log-shipper
        image: busybox:latest
        imagePullPolicy: IfNotPresent
        restartPolicy: Always
        command: [sh, -c, 'trap "exit 0" TERM; while true; do sleep 1; done']
      containers:
      - name: migrate
        image: postgres:18.4
        imagePullPolicy: IfNotPresent
        env: [{name: PGPASSWORD, value: changeit}]
        command: [sh, -c, 'psql -h astronomy-db -U postgres -d astronomy_db -v ON_ERROR_STOP=1 -c ANALYZE']
EOF
kubectl wait --for=condition=complete job/ledger-migrate-7 --timeout=120s
kubectl rollout status deployment/accounting --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/hard-job-sidecar-never-completes-127` passes.
