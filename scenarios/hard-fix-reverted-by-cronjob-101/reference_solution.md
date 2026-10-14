# Reference solution: hard-fix-reverted-by-cronjob-101

**Payment port misconfigured, and a config-sync CronJob re-applies the bad value every minute**

**Root cause:** payment listens on 8081 while its Service targets 8080. A CronJob (payment-config-sync, labelled as platform automation) PATCHes PAYMENT_PORT=8081 back every minute, so fixing the Deployment alone is undone within 60 seconds.

## How a careful SRE finds it

1. checkout logs: charging the card fails with 'connection refused' to the payment Service.
2. payment logs say it listens on 8081; `kubectl get svc payment` targets 8080. Env PAYMENT_PORT=8081.
3. Once the env var is corrected, checkout recovers, but within a minute payment rolls again and breaks.
4. `kubectl rollout history deployment/payment`, the deployment's managedFields (manager 'curl') and `kubectl get cronjobs,jobs` show payment-config-sync re-applying the bad value every minute.

## Traps (why this is hard)

- Fixing only the Deployment: passes for under a minute, then the verifier's hold/stability check fails.
- Not verifying after the fix: the re-break happens after the agent declares success.

## Fix

Stop the payment-config-sync CronJob (delete or suspend it, and make sure none of its Jobs is still running) and set PAYMENT_PORT back to 8080.

```bash
kubectl delete cronjob payment-config-sync --cascade=foreground --wait --timeout=120s
kubectl set env deployment/payment PAYMENT_PORT=8080
kubectl rollout status deployment/payment --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-fix-reverted-by-cronjob-101` passes.
