# Reference solution: hard-allowlist-forgets-checkout-106

**A zero-trust allow-list on product-catalog forgets checkout; a 'risky' payment deploy takes the blame**

**Root cause:** NetworkPolicy product-catalog-allow-clients admits only frontend and recommendation, so checkout's product lookups time out. Browsing works because the frontend is allowed. The payment rollout with a scary change-cause happened at the same time but is harmless.

## How a careful SRE finds it

1. checkout logs: preparing the order fails getting products from product-catalog (deadline exceeded).
2. product-catalog is healthy and the frontend reaches it (browse works): the failure is client-specific.
3. `kubectl get networkpolicy` shows product-catalog-allow-clients; its allow-list omits checkout.
4. Add checkout to the allow-list (removing the policy also works, but weakens the zero-trust change).

## Traps (why this is hard)

- Rolling back payment because of its recent 'SDK bump' (a decoy; counts as a distractor touch).
- Restarting checkout or product-catalog (changes nothing).

## Noise in this scenario (not the cause)

- payment rolled out minutes earlier with a risky-sounding change-cause

## Fix

```bash
kubectl patch networkpolicy product-catalog-allow-clients --type=json -p '[{"op":"add","path":"/spec/ingress/0/from/0/podSelector/matchExpressions/0/values/-","value":"checkout"}]'
```

## Confirm

`python verifiers/verify.py scenarios/hard-allowlist-forgets-checkout-106` passes.
