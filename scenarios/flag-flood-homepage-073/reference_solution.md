# Reference solution: flag-flood-homepage-073

**Synthetic traffic flood against the homepage (loadGeneratorFloodHomepage)**

**Root cause:** The `loadGeneratorFloodHomepage` flag makes the load generator send 100 homepage requests per task, an internal traffic flood that looks like an attack.

## How to find it

1. frontend-proxy access logs / Locust stats: homepage request rate far above normal, all from the load generator.
2. Feature Flags UI: `loadGeneratorFloodHomepage` is on.

## Fix

```bash
python injectors/toggle_flag.py loadGeneratorFloodHomepage --off
```

## Confirm

`python verifiers/verify.py scenarios/flag-flood-homepage-073` passes.
