# Reference solution: k8s-oom-cascade-001

**Root cause:** the cart Deployment's memory limit was set to 3Mi, far below
what the service needs to even start, and it was rolled out with the Recreate
strategy, so the old healthy pod is gone. Every start attempt is OOM-killed,
so the cart, and with it checkout, is down.

1. Reproduce: adding to cart and placing an order fail.
2. `kubectl get pods`: cart is `RunContainerError` / `CrashLoopBackOff`, with a
   rising restart count.
3. `kubectl describe pod -l opentelemetry.io/name=cart`: `Last State: Terminated,
   Reason: StartError` and the event
   `container init was OOM-killed (memory limit too low?)`.
   (With a less extreme limit you would see `Reason: OOMKilled, Exit Code: 137`
   after the service has run for a while. It is the same root cause.)
4. `kubectl get deploy cart -o jsonpath='{.spec.template.spec.containers[0].resources}'`:
   `limits.memory: 3Mi`.
5. Fix: give it a sane memory budget:
   ```
   kubectl set resources deployment/cart -c cart --limits=memory=160Mi --requests=memory=64Mi
   kubectl rollout status deployment/cart
   ```
6. Confirm: the cart pod stays Running without restarts, and cart and checkout work.

`kubectl rollout undo deployment/cart` also works (it restores the previous
template).
