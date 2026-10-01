# Reference solution: flag-image-slow-load-071

**Images served with an artificial delay (imageSlowLoad)**

**Root cause:** The `imageSlowLoad` flag is read by the shop's browser code, which then sends every image request with `x-envoy-fault-delay-request: 10000`. The Envoy edge proxy honours that header and holds each image for 10 seconds. The image server itself is fast.

## How to find it

1. Only image requests are slow; the rest of each page is fast.
2. The browser dev tools / frontend-proxy logs: image requests carry `x-envoy-fault-delay-request`; image-provider's own response time is milliseconds.
3. Feature Flags UI: `imageSlowLoad` is at 10sec.

## Fix

```bash
python injectors/toggle_flag.py imageSlowLoad --off
```

## Confirm

`python verifiers/verify.py scenarios/flag-image-slow-load-071` passes.
