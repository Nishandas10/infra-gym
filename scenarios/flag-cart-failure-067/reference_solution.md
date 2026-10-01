# Reference solution: flag-cart-failure-067

**Cart service errors (cartFailure)**

**Root cause:** The `cartFailure` flag (at 100%) makes the cart service fail its operations on purpose.

## How to find it

1. cart logs / Jaeger: cart RPC errors carrying the feature-flag attribute.
2. Pods are healthy, and valkey-cart is healthy.
3. Feature Flags UI: `cartFailure` is at 100%.

## Fix

```bash
python injectors/toggle_flag.py cartFailure --off
```

## Confirm

`python verifiers/verify.py scenarios/flag-cart-failure-067` passes.
