# Reference solution: pay-fail-006

**Root cause:** the `paymentFailure` feature flag was switched to `100%`, so the
payment service rejects every charge request.

1. Reproduce: place an order in the shop (or `POST /api/checkout`). It fails with a
   payment error, while browsing and the cart work.
2. `kubectl get pods`: every pod is Running, so this is not a crash.
3. `kubectl logs deploy/checkout --tail=50` shows the charge call to `payment` failing;
   `kubectl logs deploy/payment --tail=50` shows the service returning errors on purpose
   (the flag is evaluated there).
4. Open the Feature Flags UI (`http://localhost:8080/feature/`) or read flagd's answer:
   `paymentFailure` is at `100%` instead of `off`.
5. Fix: turn the flag off (UI toggle, or):
   ```
   python injectors/toggle_flag.py paymentFailure --off
   ```
6. Confirm: place an order; it succeeds.

In a real incident step 5 is "roll back the config change that enabled the bad
behaviour".
