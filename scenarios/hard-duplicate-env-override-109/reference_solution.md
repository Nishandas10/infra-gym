# Reference solution: hard-duplicate-env-override-109

**A duplicate env entry from an old overlay silently overrides the correct value**

**Root cause:** recommendation's env list defines PRODUCT_CATALOG_ADDR twice: the original product-catalog:8080 and, at the end, product-catalog:3550 (the old v1 port from a stale overlay). The last definition wins. The ConfigMap recommendation-settings also says 8080, but explicit env always overrides envFrom.

## How a careful SRE finds it

1. recommendation logs: cannot reach product-catalog:3550 (connection refused / unavailable).
2. `kubectl get deploy recommendation -o yaml` shows PRODUCT_CATALOG_ADDR twice; the effective value is the last one (`kubectl exec deploy/recommendation -- env | grep PRODUCT_CATALOG`).
3. The ConfigMap is correct and irrelevant: explicit env beats envFrom.
4. Remove the duplicate (or `kubectl set env` the variable), then let it roll out.

## Traps (why this is hard)

- Editing the ConfigMap, which already says 8080 (no effect).
- Reading only the first PRODUCT_CATALOG_ADDR entry and concluding the config is fine.

## Noise in this scenario (not the cause)

- a correct-looking ConfigMap wired in via envFrom

## Fix

```bash
kubectl get deployment recommendation -o json | python3 -c 'import json,sys; d=json.load(sys.stdin); c=d["spec"]["template"]["spec"]["containers"][0]; seen=set(); env=[]; [env.append(e) or seen.add(e["name"]) for e in c["env"] if e["name"] not in seen]; c["env"]=env; print(json.dumps(d))' | kubectl replace -f -
kubectl rollout status deployment/recommendation --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-duplicate-env-override-109` passes.
