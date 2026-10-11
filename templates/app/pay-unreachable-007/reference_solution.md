# Reference solution: pay-unreachable-007

**Root cause:** the `paymentUnreachable` flag makes checkout call the payment
service at an address where nothing is listening. The payment pod itself is
healthy, which is the trap: "payment is up" is true but irrelevant.

1. Reproduce: `POST /api/checkout` (or place an order in the UI) fails after a delay.
2. `kubectl get pods`: payment and checkout are both Running.
3. `kubectl logs deploy/checkout --tail=50`: the charge call fails with a
   connection/unavailable error, not a payment decline.
4. Jaeger (`/jaeger/ui`), service `checkout`: the `PaymentService/Charge` span
   errors without ever reaching the payment service.
5. Feature Flags UI: `paymentUnreachable` is `on`.
6. Fix:
   ```
   python injectors/toggle_flag.py paymentUnreachable --off
   ```
7. Confirm an order goes through.
