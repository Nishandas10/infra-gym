# Reference solution: flag-intl-shipping-slow-072

**International shipping quotes delayed (intlShippingSlowdown)**

**Root cause:** The `intlShippingSlowdown` flag makes shipping delay quotes for non-US addresses by 10 seconds. It only affects some customers, so aggregate latency barely moves.

## How to find it

1. Jaeger: shipping spans are ~10s only for orders with a non-US address.
2. US orders are fast.
3. Feature Flags UI: `intlShippingSlowdown` is at 10sec.

## Fix

```bash
python injectors/toggle_flag.py intlShippingSlowdown --off
```

## Confirm

`python verifiers/verify.py scenarios/flag-intl-shipping-slow-072` passes.
