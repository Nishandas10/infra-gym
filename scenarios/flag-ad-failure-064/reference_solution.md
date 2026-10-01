# Reference solution: flag-ad-failure-064

**Ad service fails every request (feature flag adFailure)**

**Root cause:** The `adFailure` feature flag is on, so the ad service fails about one in ten GetAds calls on purpose. The failure is intermittent, so small samples often look healthy.

## How to find it

1. ad logs: errors on some GetAds calls; frontend `/api/data` returns 500 now and then.
2. Error rate over many requests is ~10%, not 100%.
3. Nothing restarted and nothing was deployed.
4. Feature Flags UI: `adFailure` is on.

## Fix

```bash
python injectors/toggle_flag.py adFailure --off
```

## Confirm

`python verifiers/verify.py scenarios/flag-ad-failure-064` passes.
