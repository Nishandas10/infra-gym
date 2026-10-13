# Reference solution: hard-cart-chained-addr-auth-103

**A mistyped cart datastore port hides a half-finished credential rotation behind it**

**Root cause:** Two layers. (1) cart's VALKEY_ADDR points at port 6380 (connection refused). (2) valkey-cart now requires a password (rotated this morning, stored in Secret valkey-cart-credentials) that cart was never given. Fixing the port alone turns 'connection refused' into NOAUTH errors.

## How a careful SRE finds it

1. cart logs: connection refused to valkey-cart:6380; the Service and valkey listen on 6379.
2. Once VALKEY_ADDR is corrected, cart fails with NOAUTH / authentication required.
3. `kubectl get secrets` shows valkey-cart-credentials, annotated as rotated this morning for consumer 'cart'.

## Traps (why this is hard)

- Declaring victory after the port fix without re-testing (the second layer is still there).
- Restarting valkey-cart to drop the password: it works but throws away every customer's cart.

## Fix

Set cart's VALKEY_ADDR back to valkey-cart:6379; then either roll the password rotation back (clear requirepass using the stored password) or give cart the password, and restart cart so it reconnects.

```bash
kubectl set env deployment/cart VALKEY_ADDR=valkey-cart:6379
kubectl exec deploy/valkey-cart -- valkey-cli -a "$(kubectl get secret valkey-cart-credentials -o jsonpath='{.data.password}' | base64 -d)" --no-auth-warning CONFIG SET requirepass ''
kubectl rollout restart deployment/cart
kubectl rollout status deployment/cart --timeout=300s
```

## Confirm

`python verifiers/verify.py scenarios/hard-cart-chained-addr-auth-103` passes.
