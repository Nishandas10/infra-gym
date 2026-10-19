# Reference solution: hard-flag-targeting-rule-132

**Almost every card payment is declined, while the payment flag reads off**

**Root cause:** The paymentFailure flag still has `defaultVariant` off, which is what a quick look at the flag shows, but it gained a `targeting` rule (`$flagd.timestamp >= <a time 10 minutes before>`) that serves the 90% variant to every evaluation, so the payment service declines about 95% of charges. The rule is in flagd's live file and in the flagd-config ConfigMap that flagd loads at start, so restarting flagd brings it straight back.

## How a careful SRE finds it

1. payment logs: most charges fail with the feature-flag-driven error; a few succeed.
2. flagd's OFREP API (POST /ofrep/v1/evaluate/flags/paymentFailure) returns variant 90% with reason TARGETING_MATCH, not DEFAULT.
3. The flagd-config ConfigMap and the live file show paymentFailure with defaultVariant off and a targeting rule.

## Traps (why this is hard)

- Reading only defaultVariant (off) and ruling the flag out.
- Restarting flagd: it reloads the same rule from the ConfigMap.
- Fixing only the live flag file: passes now, fails after the verifier restarts flagd.

## Fix

Remove the targeting rule of paymentFailure (or make it serve off) in the flagd-config ConfigMap, the source of truth, and restart flagd; or fix both the ConfigMap and the live file. Fixing only the live file does not survive a flagd restart.

```bash
kubectl get configmap flagd-config -o yaml | sed 's/^\(\s*\)"90%",$/\1"off",/' | kubectl apply -f -
sleep 20
kubectl rollout restart deployment/flagd
kubectl rollout status deployment/flagd --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/hard-flag-targeting-rule-132` passes.
