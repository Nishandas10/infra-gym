# Reference solution: hard-flag-in-source-of-truth-111

**Half of card payments are declined; a live fix does not survive the next restart**

**Root cause:** The feature flag paymentFailure is set to 50% in the flagd-config ConfigMap, the source flagd loads at startup. Flipping the flag only in flagd's live file (the Feature Flags UI / flagd-ui) fixes payments until flagd restarts, then the ConfigMap brings the failure back.

## How a careful SRE finds it

1. payment logs: about half of charges fail with the feature-flag-driven error.
2. flagd's OFREP API (POST /ofrep/v1/evaluate/flags/paymentFailure) returns variant 50%.
3. The live file in the flagd-ui container and the flagd-config ConfigMap both say 50%.

## Traps (why this is hard)

- Fixing only the live flag file: passes now, fails after the verifier restarts flagd.
- Fixing only the ConfigMap without restarting flagd: nothing changes until the next restart.

## Fix

Set paymentFailure to off in the flagd-config ConfigMap (the source of truth) and restart flagd, or fix both the ConfigMap and the live file. Fixing only the live file does not survive a flagd restart.

```bash
python injectors/source_flag.py paymentFailure off
```

## Confirm

`python verifiers/verify.py scenarios/hard-flag-in-source-of-truth-111` passes.
