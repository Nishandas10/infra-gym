# Reference solution: flag-ad-high-cpu-065

**Ad service burns CPU on every request (adHighCpu)**

**Root cause:** The `adHighCpu` flag makes the ad service run a CPU-heavy loop on requests, which saturates its CPU.

## How to find it

1. Grafana / kubelet stats: ad container CPU far above baseline.
2. Jaeger: GetAds spans are long, with an attribute showing the high-CPU path.
3. Feature Flags UI: `adHighCpu` is on.

## Fix

```bash
python injectors/toggle_flag.py adHighCpu --off
```

## Confirm

`python verifiers/verify.py scenarios/flag-ad-high-cpu-065` passes.
