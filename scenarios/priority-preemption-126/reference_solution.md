# Reference solution: priority-preemption-126

**A nightly batch with a copied high-priority class preempts the whole shop off both workers**

**Root cause:** A `nightly-batch` Deployment was added with `priorityClassName: batch-critical`, a class copied from the platform's critical one (value 1000000). Its two replicas (one per worker) each request 31Gi of a worker's 32Gi. To place them, the scheduler preempted every lower-priority pod on both workers: the whole shop. The evicted pods were recreated but stay Pending with Insufficient memory, so every page fails. Nothing in the shop itself changed.

## How to find it

1. `kubectl get pods`: almost every shop pod Pending; `nightly-batch` 2/2 Running.
2. `kubectl describe pod <pending shop pod>`: 0/3 nodes are available ... Insufficient memory; preemption is not helpful (the batch has a higher priority).
3. `kubectl get events --field-selector reason=Preempted`: shop pods preempted by the nightly-batch pods.
4. `kubectl get deploy nightly-batch -o yaml`: priorityClassName batch-critical, requests 31Gi; `kubectl get priorityclass`: batch-critical 1000000.

## Noise in this scenario (not the cause)

- The shop's own Deployments and resources are unchanged; raising their priority or memory is neither possible nor needed.

## Fix

Remove the batch from the shop's capacity: delete the nightly-batch Deployment or scale it to 0. The shop's pods then schedule again and the shop recovers within a few minutes. Removing only its priorityClassName does not help by itself: the running batch pods keep their memory until they are replaced. The PriorityClass cannot be deleted with the on-call permissions here, and does not need to be.

```bash
kubectl delete deployment nightly-batch
```

## Confirm

`python verifiers/verify.py scenarios/priority-preemption-126` passes.
