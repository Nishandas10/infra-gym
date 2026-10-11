# Reference solution: kafka-backlog-010

**Root cause:** the `kafkaQueueProblems` flag makes checkout flood the `orders`
topic with duplicate messages and slows the consumers down. Checkout keeps
returning success; the damage is downstream and silent.

1. Checkout works (`POST /api/checkout` returns an order ID). Don't stop there.
2. Check the consumers' lag (from any pod with the Kafka CLIs; the gym uses
   `gym-system/gym-kafka-tools`):
   ```
   kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group fraud-detection
   ```
   LAG grows by hundreds or thousands.
3. `kubectl logs deploy/fraud-detection --tail=50`: it is consuming, just slowly.
   `kubectl logs deploy/checkout --tail=50`: it sends many messages per order.
4. Feature Flags UI: `kafkaQueueProblems` is on.
5. Fix:
   ```
   python injectors/toggle_flag.py kafkaQueueProblems --off
   ```
6. Confirm the lag drains back to near zero (this takes a few minutes).
