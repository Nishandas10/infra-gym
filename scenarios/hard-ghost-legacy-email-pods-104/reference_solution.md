# Reference solution: hard-ghost-legacy-email-pods-104

**Leftover legacy pods still match the email Service and swallow part of the traffic**

**Root cause:** Deployment email-v1-legacy (left over from a migration) has pods labelled opentelemetry.io/name=email, so the email Service load-balances to them too. They answer every request with an HTTP error, so roughly half of the confirmation emails fail.

## How a careful SRE finds it

1. Calling the email Service repeatedly (e.g. from a temporary pod) fails about half the time.
2. The real email pod's logs show only successful sends; checkout logs show some send failures.
3. `kubectl get endpoints email` lists two pod IPs; `kubectl get pods -l opentelemetry.io/name=email` shows an extra pod from Deployment email-v1-legacy (busybox, old version label).
4. Remove the legacy Deployment (or relabel it out of the Service).

## Traps (why this is hard)

- Restarting the real email Deployment: nothing changes.
- Testing once and concluding the service is fine (the failure is intermittent).

## Fix

```bash
kubectl delete deployment email-v1-legacy
```

## Confirm

`python verifiers/verify.py scenarios/hard-ghost-legacy-email-pods-104` passes.
