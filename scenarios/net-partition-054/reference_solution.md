# Reference solution: net-partition-054

**Network partition between two specific services**

**Root cause:** A NetworkChaos partition drops all traffic between the checkout and payment pods, in both directions. Each side can still talk to everything else.

## How to find it

1. checkout logs: payment calls time out.
2. A test call to payment from another pod succeeds, so the problem is specific to the checkout-payment path.
3. `kubectl get networkchaos -A`: `checkout-payment-partition`.

## Fix

```bash
kubectl delete networkchaos.chaos-mesh.org checkout-payment-partition
```

## Confirm

`python verifiers/verify.py scenarios/net-partition-054` passes.
