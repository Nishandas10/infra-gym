# Reference solution: flag-image-slow-load-071

**Images served with an artificial delay (imageSlowLoad)**

**Root cause:** The `imageSlowLoad` flag is read by the shop's browser code, which then sends every image request with `x-envoy-fault-delay-request: 10000`. The Envoy edge proxy honours that header and holds each image for 10 seconds. The image server itself is fast.

## How to find it

1. Only image requests are slow for customers; the rest of each page is fast.
2. An image fetched through frontend-proxy with curl is fast: the delay applies only to requests that carry the header the browser code adds. image-provider answers in milliseconds.
3. flagd's live flag file (`/app/data/demo.flagd.json`, flagd pod, container flagd-ui) or the Feature Flags UI: `imageSlowLoad` is at 10sec. The change is live only: restarting flagd reloads the default (off) from its ConfigMap.
4. frontend-proxy writes no access log in this world, so the slow requests do not show in its logs.

## Fix

```bash
python injectors/toggle_flag.py imageSlowLoad --off
```

## Confirm

`python verifiers/verify.py scenarios/flag-image-slow-load-071` passes.
