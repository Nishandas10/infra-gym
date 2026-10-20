# Diagnosis scores (hard-v1)

Judge: claude-sonnet-5-5, rubric v2. The judge saw only the answer key, the incident prompt and the model's written report (no model name, no PASS/FAIL). Pass rate comes from the verifier and is not affected by the judge.


| Model | Episodes | Pass rate | Root cause correct | Location correct | Mechanism correct | Diagnosis score | Fixed + understood | Fixed, cause wrong/unstated | Blamed noise | Judge votes split |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 24 | 23/24 (96%) | 22/24 (92%) | 23/24 | 22/24 | 0.94 | 22/24 | 0/24 | 0 | 0 |
| claude-sonnet-5-5 | 16 | 14/16 (88%) | 15/16 (94%) | 15/16 | 15/16 | 0.97 | 14/16 | 0/16 | 0 | 0 |
| deepseek-v4-pro | 16 | 12/16 (75%) | 12/16 (75%) | 12/16 | 12/16 | 0.81 | 12/16 | 0/16 | 0 | 0 |
| gemini-4-argon | 16 | 16/16 (100%) | 16/16 (100%) | 16/16 | 16/16 | 1.00 | 16/16 | 0/16 | 0 | 0 |
| moonshotai/kimi-k3 | 16 | 12/16 (75%) | 11/16 (69%) | 12/16 | 12/16 | 0.81 | 11/16 | 0/16 | 1 | 0 |
| openai/gpt-6.1-sol | 16 | 15/16 (94%) | 15/16 (94%) | 15/16 | 15/16 | 0.97 | 15/16 | 0/16 | 0 | 0 |
| z-ai/glm-5.3 | 16 | 15/16 (94%) | 12/16 (75%) | 12/16 | 12/16 | 0.81 | 12/16 | 2/16 | 0 | 0 |

Diagnosis score: correct = 1, partial = 0.5, wrong or missing = 0, averaged over episodes.


## Every episode

| Scenario | Model | Verifier | Root cause | Outcome | Judge's evidence |
|---|---|---|---|---|---|
| hard-allowlist-forgets-checkout-106 | claude-opus-5-5 | PASS | correct | Fixed + understood | `product-catalog-allow-clients` ... only lets pods labelled ... `frontend` or `recommendation` connect to product-catalog on port 8080. It l |
| hard-cart-chained-addr-auth-103 | claude-opus-5-5 | PASS | correct | Fixed + understood | A `kubectl patch` changed cart's `VALKEY_ADDR` to `valkey-cart:6380`... valkey-cart now requires a password... cart was never given it. |
| hard-duplicate-env-override-109 | claude-opus-5-5 | PASS | correct | Fixed + understood | a second `PRODUCT_CATALOG_ADDR=product-catalog:3550` entry to the end of the `recommendation` Deployment's environment variables... Kubernet |
| hard-egress-policy-blocks-db-102 | claude-opus-5-5 | PASS | correct | Fixed + understood | NetworkPolicy `product-catalog-egress-hardening` ... leaves out PostgreSQL port 5432. That blocks product-catalog from opening new connectio |
| hard-fix-reverted-by-cronjob-101 | claude-opus-5-5 | PASS | correct | Fixed + understood | Each run changes the `payment` Deployment to set `PAYMENT_PORT=8081`... The `payment` Service and the container's declared port both still u |
| hard-flag-in-source-of-truth-111 | claude-opus-5-5 | PASS | correct | Fixed + understood | In `flagd-config`, the `paymentFailure` flag's default setting (`defaultVariant`) had been changed from "off" to "50%". |
| hard-flag-targeting-rule-132 | claude-opus-5-5 | PASS | partial | Fixed, cause half-explained | The change switched the `paymentFailure` flag from `"off"` to its `"90%"` setting... The flag still contains a timestamp rule |
| hard-flag-targeting-rule-132 | claude-opus-5-5 | PASS | correct | Fixed + understood | added a time-based rule to that flag: once the time passed 1792412578 (12:22:58 UTC), it switched to the "90%" setting... flag's normal sett |
| hard-flag-targeting-rule-132 | claude-opus-5-5 | PASS | correct | Fixed + understood | added a time-triggered rule to the `paymentFailure` flag: once the clock passed 1792413021, every lookup returned the `"90%"` setting instea |
| hard-ghost-legacy-email-pods-104 | claude-opus-5-5 | PASS | correct | Fixed + understood | Its pods carried the label `opentelemetry.io/name: email`, which is exactly what the `email` Service uses to pick its pods. So the Service h |
| hard-job-sidecar-never-completes-127 | claude-opus-5-5 | PASS | correct | Fixed + understood | the Job's pod also has a `log-shipper` helper container that loops forever and never exits on its own. A Job only counts as Complete when ev |
| hard-kafka-consumer-quota-130 | claude-opus-5-5 | PASS | correct | Fixed + understood | a Kafka quota that limited client-id `rdkafka` to 1 byte per second for reading (`consumer_byte_rate=1.0`). `rdkafka` is the name the accoun |
| hard-kafka-consumer-quota-130 | claude-opus-5-5 | PASS | correct | Fixed + understood | Kafka client quota of `consumer_byte_rate=1.0` (1 byte per second) on client-id `rdkafka`. That's the client ID the accounting service uses |
| hard-kafka-consumer-quota-130 | claude-opus-5-5 | FAIL | wrong | Not fixed | the most likely cause is that accounting's existing Kafka connection hung and the client never gave up on it and reconnected |
| hard-masked-second-fault-107 | claude-opus-5-5 | PASS | correct | Fixed + understood | checkout deployment had `PRODUCT_CATALOG_ADDR=product-catalog:9090`... shipping service's target port to 8888. The shipping app listens on 8 |
| hard-mutating-policy-rewrites-pods-131 | claude-opus-5-5 | PASS | correct | Fixed + understood | a cluster-wide admission rule (a MutatingAdmissionPolicy) called `platform-pod-defaults`, plus the binding... it overwrites `PAYMENT_ADDR` w |
| hard-mutating-policy-rewrites-pods-131 | claude-opus-5-5 | PASS | correct | Fixed + understood | a cluster-wide rule called `platform-pod-defaults`. It's a MutatingAdmissionPolicy... changed the payment address from `payment:8080` to `pa |
| hard-mutating-policy-rewrites-pods-131 | claude-opus-5-5 | PASS | correct | Fixed + understood | someone created a cluster-wide rule called `platform-pod-defaults`... changed their payment address (`PAYMENT_ADDR`) from `payment:8080` to  |
| hard-oom-fix-blocked-by-limitrange-110 | claude-opus-5-5 | PASS | correct | Fixed + understood | cut the `ad` deployment's memory limit ... to 48Mi ... LimitRange `namespace-container-limits` ... caps every container at 128Mi ... would h |
| hard-oom-fix-blocked-by-limitrange-110 | claude-opus-5-5 | PASS | correct | Fixed + understood | cut the `ad` deployment's memory limit from 450Mi to 48Mi... LimitRange, `namespace-container-limits`, that capped every container in `defau |
| hard-oom-fix-blocked-by-limitrange-110 | claude-opus-5-5 | PASS | correct | Fixed + understood | cut its memory limit to **48Mi**... LimitRange `namespace-container-limits`... capped every container in the namespace at 128Mi... a pod ask |
| hard-pinned-endpoints-108 | claude-opus-5-5 | PASS | correct | Fixed + understood | The `quote` Service's selector was removed... `quote-pinned` was applied... sent all `quote` traffic to 10.244.250.17, and no pod has that I |
| hard-silent-ledger-write-denied-105 | claude-opus-5-5 | PASS | correct | Fixed + understood | INSERT permission on the `accounting."order"` table had been removed with `REVOKE INSERT ON accounting."order" FROM astronomy_user` |
| hard-telemetry-noise-hides-scheduling-112 | claude-opus-5-5 | PASS | correct | Fixed + understood | added the taint `dedicated=batch:NoSchedule` ... no node could take shop pods ... the new currency pod couldn't start. |
| hard-allowlist-forgets-checkout-106 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | allowed ingress to `product-catalog` only from `frontend` and `recommendation`. The `checkout` service also calls `product-catalog`... traff |
| hard-cart-chained-addr-auth-103 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `cart` deployment's `VALKEY_ADDR` was `valkey-cart:6380`... Valkey now requires a password... The cart wasn't configured to send it, so  |
| hard-duplicate-env-override-109 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `recommendation` Deployment defined `PRODUCT_CATALOG_ADDR` twice... A second, later entry set it to `product-catalog:3550`, and the late |
| hard-egress-policy-blocks-db-102 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | `product-catalog-egress-hardening`... limited their egress to DNS and to ports 8080, 4317... That left out Postgres on port 5432. |
| hard-fix-reverted-by-cronjob-101 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | the `payment-config-sync` CronJob runs every minute. It patches the `payment` Deployment to set `PAYMENT_PORT=8081`. The `payment` Service.. |
| hard-flag-in-source-of-truth-111 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | In the `flagd-config` ConfigMap, `paymentFailure` had `defaultVariant: "50%"`... I restarted the `flagd` deployment so it picked up the chan |
| hard-flag-targeting-rule-132 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `paymentFailure` flag had a `targeting` rule. Once `$flagd.timestamp` passed 1792480411, the rule returned the `90%` variant |
| hard-ghost-legacy-email-pods-104 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `email-v1-legacy` deployment ... pod template carried the label `opentelemetry.io/name: email`, which is the Service's selector... answe |
| hard-job-sidecar-never-completes-127 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The job's second container, a `log-shipper` sidecar, runs `while true; do sleep 1; done` and never exits. The pod therefore stayed running,  |
| hard-kafka-consumer-quota-130 | claude-sonnet-5-5 | FAIL | correct | Understood, not fixed | Someone had set a Kafka client quota on client-id `rdkafka` with `consumer_byte_rate=1`... The accounting service's Kafka consumer uses that |
| hard-masked-second-fault-107 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | the `shipping` Service had `targetPort: 8888`, but the shipping container listens on 8080... checkout Deployment had `PRODUCT_CATALOG_ADDR=p |
| hard-mutating-policy-rewrites-pods-131 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | A `MutatingAdmissionPolicy` named `platform-pod-defaults` ... At pod creation it overwrites the container's `PAYMENT_ADDR` with `payment:808 |
| hard-oom-fix-blocked-by-limitrange-110 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `ad` deployment had a memory limit of 48Mi... A LimitRange called `namespace-container-limits` capped every container at 128Mi, so the n |
| hard-pinned-endpoints-108 | claude-sonnet-5-5 | FAIL | partial | Not fixed | The `quote` Service in `default` had lost its pod selector, so it had no endpoints. |
| hard-silent-ledger-write-denied-105 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | That user had no INSERT privilege on `accounting."order"`... Every insert failed with `42501: permission denied for table order` |
| hard-telemetry-noise-hides-scheduling-112 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `worker` and `worker2` nodes carry the taint `dedicated=batch:NoSchedule`... The pod had no matching toleration, so it couldn't be sched |
| hard-allowlist-forgets-checkout-106 | deepseek-v4-pro | PASS | correct | Fixed + understood | NetworkPolicy `product-catalog-allow-clients` was restricting ingress to the product-catalog pods, allowing only pods labeled `frontend` and |
| hard-cart-chained-addr-auth-103 | deepseek-v4-pro | FAIL | partial | Not fixed | the `cart` Deployment was configured with `VALKEY_ADDR=valkey-cart:6380`, but the `valkey-cart` Service only exposes port `6379` |
| hard-duplicate-env-override-109 | deepseek-v4-pro | PASS | correct | Fixed + understood | `PRODUCT_CATALOG_ADDR` defined twice in its container env. The first value was correct (`product-catalog:8080`), but the later duplicate was |
| hard-egress-policy-blocks-db-102 | deepseek-v4-pro | PASS | correct | Fixed + understood | NetworkPolicy `product-catalog-egress-hardening` ... allowed only DNS plus ports 8080, 4317, ... 443. It omitted TCP 5432, so the product-ca |
| hard-fix-reverted-by-cronjob-101 | deepseek-v4-pro | FAIL | partial | Not fixed | the `payment` Deployment had `PAYMENT_PORT=8081`, so the payment service listened on port 8081, but the `payment` Service ... expected port  |
| hard-flag-in-source-of-truth-111 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `flagd-config` ConfigMap had the `paymentFailure` feature flag enabled with `defaultVariant: "50%"` |
| hard-flag-targeting-rule-132 | deepseek-v4-pro | PASS | correct | Fixed + understood | `paymentFailure` targeted the `"90%"` variant (with probability `0.95`) once `$flagd.timestamp >= 1792402325`, so ~95% of payment charge req |
| hard-ghost-legacy-email-pods-104 | deepseek-v4-pro | PASS | correct | Fixed + understood | `email-v1-legacy` Deployment (busybox `httpd`) also had that label on its pod template... requests hitting the legacy pod returned HTTP 501 |
| hard-job-sidecar-never-completes-127 | deepseek-v4-pro | PASS | correct | Fixed + understood | a second `log-shipper` container was running `while true; do sleep 1; done`, so the Job never completed. As a result, accounting was not run |
| hard-kafka-consumer-quota-130 | deepseek-v4-pro | FAIL | wrong | Not fixed | Kafka records from offset 8 onward looked binary/protobuf-encoded, while the accounting service expects JSON, so the consumer stalled on the |
| hard-masked-second-fault-107 | deepseek-v4-pro | PASS | correct | Fixed + understood | checkout was configured with `PRODUCT_CATALOG_ADDR=product-catalog:9090`... shipping Service targetPort was 8888 while the shipping pod list |
| hard-mutating-policy-rewrites-pods-131 | deepseek-v4-pro | FAIL | wrong | Not fixed | this indicates a mutating admission webhook (likely `chaos-mesh-mutation`) is overriding the env var during pod creation |
| hard-oom-fix-blocked-by-limitrange-110 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `ad` Deployment had its container memory limit set to `48Mi`... LimitRange `namespace-container-limits` capping container memory at `128 |
| hard-pinned-endpoints-108 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `quote` Service had lost its pod selector and was relying on a manually pinned, stale EndpointSlice (`quote-pinned`) pointing at old IP  |
| hard-silent-ledger-write-denied-105 | deepseek-v4-pro | PASS | correct | Fixed + understood | its DB user `astronomy_user` was missing the `INSERT` privilege on `accounting."order"`... every accounting write failed with: 42501: permis |
| hard-telemetry-noise-hides-scheduling-112 | deepseek-v4-pro | PASS | correct | Fixed + understood | worker nodes had been tainted `dedicated=batch:NoSchedule`, which made the `currency` pod unschedulable (so the `currency` Service had no en |
| hard-allowlist-forgets-checkout-106 | gemini-4-argon | PASS | correct | Fixed + understood | Because `checkout` was omitted from the `NetworkPolicy` ingress rules, `checkout` could not reach `product-catalog` |
| hard-cart-chained-addr-auth-103 | gemini-4-argon | PASS | correct | Fixed + understood | VALKEY_ADDR in Deployment/cart was set to valkey-cart:6380, whereas valkey-cart listens on 6379... requirepass was enabled ... Deployment/ca |
| hard-duplicate-env-override-109 | gemini-4-argon | PASS | correct | Fixed + understood | a second duplicate `PRODUCT_CATALOG_ADDR` entry at the end of the container's `env` list set the value to `product-catalog:3550` |
| hard-egress-policy-blocks-db-102 | gemini-4-argon | PASS | correct | Fixed + understood | omitting PostgreSQL port `5432/TCP` (for `astronomy-db`)... `product-catalog` could not establish database connections to `astronomy-db:5432 |
| hard-fix-reverted-by-cronjob-101 | gemini-4-argon | PASS | correct | Fixed + understood | a CronJob (`payment-config-sync`) running every minute ... continuously patching `deployment/payment` ... to set `PAYMENT_PORT` back to "808 |
| hard-flag-in-source-of-truth-111 | gemini-4-argon | PASS | correct | Fixed + understood | In the `flagd-config` ConfigMap (`demo.flagd.json`), the `paymentFailure` feature flag had its `defaultVariant` set to `"50%"` |
| hard-flag-targeting-rule-132 | gemini-4-argon | PASS | correct | Fixed + understood | the `paymentFailure` feature flag had a timestamp-based `targeting` rule (`$flagd.timestamp >= 1792497057`) that evaluated the flag to the ` |
| hard-ghost-legacy-email-pods-104 | gemini-4-argon | PASS | correct | Fixed + understood | email-v1-legacy's pod template included the label `opentelemetry.io/name: email`... returns `501 Not Implemented` to `POST /send_order_confi |
| hard-job-sidecar-never-completes-127 | gemini-4-argon | PASS | correct | Fixed + understood | its `log-shipper` container ... was configured as a regular container under `spec.template.spec.containers` rather than a native sidecar ... |
| hard-kafka-consumer-quota-130 | gemini-4-argon | PASS | correct | Fixed + understood | A dynamic Kafka client quota (`consumer_byte_rate=1.0`, i.e., 1 byte/sec) was configured on the `kafka` broker for `client-id=rdkafka` |
| hard-masked-second-fault-107 | gemini-4-argon | PASS | correct | Fixed + understood | `PRODUCT_CATALOG_ADDR` ... set to `product-catalog:9090`, whereas `service/product-catalog` listens on port `8080`; `service/shipping` had i |
| hard-mutating-policy-rewrites-pods-131 | gemini-4-argon | PASS | correct | Fixed + understood | mutated the `checkout` container's `PAYMENT_ADDR` environment variable from `payment:8080` ... to `payment:8081` |
| hard-oom-fix-blocked-by-limitrange-110 | gemini-4-argon | PASS | correct | Fixed + understood | memory limit and request reduced from `450Mi` to `48Mi`... `LimitRange` named `namespace-container-limits`... maximum container memory limit |
| hard-pinned-endpoints-108 | gemini-4-argon | PASS | correct | Fixed + understood | The `quote` Service had its pod selector removed and was instead backed by a manually managed `EndpointSlice` (`quote-pinned`) pointing to a |
| hard-silent-ledger-write-denied-105 | gemini-4-argon | PASS | correct | Fixed + understood | `astronomy_user` was missing the `INSERT` privilege on the `accounting."order"` table ... `permission denied for table order` |
| hard-telemetry-noise-hides-scheduling-112 | gemini-4-argon | PASS | correct | Fixed + understood | Both worker nodes were tainted with `dedicated=batch:NoSchedule`... `currency` deployment has no matching tolerations, its pod remained stuc |
| hard-allowlist-forgets-checkout-106 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | created a NetworkPolicy `product-catalog-allow-clients` ... restricted ingress to product-catalog:8080 to ... [frontend, recommendation]. Th |
| hard-cart-chained-addr-auth-103 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | Valkey cart store had a password set (`requirepass`, ... `valkey-cart-credentials` secret), and cart ... point at the wrong port (`VALKEY_AD |
| hard-duplicate-env-override-109 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The `recommendation` Deployment contained a duplicate `PRODUCT_CATALOG_ADDR` environment variable... later bad one (`product-catalog:3550`). |
| hard-egress-policy-blocks-db-102 | moonshotai/kimi-k3 | FAIL | wrong | Not fixed | the original fault was database lock contention on `catalog.products` ... ongoing outage is that the product-catalog pod was killed ... a st |
| hard-fix-reverted-by-cronjob-101 | moonshotai/kimi-k3 | FAIL | partial | Not fixed | The `payment` Deployment had been modified ... to set the env var `PAYMENT_PORT=8081` ... No other components were touched. |
| hard-flag-in-source-of-truth-111 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | the `paymentFailure` feature flag's `defaultVariant` was changed from "off" to "50%" (numeric value 0.5) |
| hard-flag-targeting-rule-132 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | contained an injected targeting rule ... Once $flagd.timestamp ≥ 1792490763 the flag evaluated to variant "90%" ... ~95% of payment charge r |
| hard-ghost-legacy-email-pods-104 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | A leftover "legacy" deployment, `email-v1-legacy`... had been rolled out with that exact same label... registered as a second endpoint of th |
| hard-job-sidecar-never-completes-127 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | Its pod contained a `log-shipper` sidecar running `while true; do sleep 1; done` — an infinite loop that never exits — so ... the pod/job st |
| hard-kafka-consumer-quota-130 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | a dynamic client config set `consumer_byte_rate=1.0` (1 byte/sec) for client-id `rdkafka`, which is exactly the client-id used by the `accou |
| hard-masked-second-fault-107 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | checkout Deployment had PRODUCT_CATALOG_ADDR=product-catalog:9090 ... service/shipping had targetPort: 8888 while the shipping container lis |
| hard-mutating-policy-rewrites-pods-131 | moonshotai/kimi-k3 | FAIL | partial | Not fixed | pods created from them consistently come up with `8081`, pointing to an admission-time mutation; the cluster has Chaos Mesh mutating webhook |
| hard-oom-fix-blocked-by-limitrange-110 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | cut the `ad` container's memory limit/request down to **48Mi** ... LimitRange (`namespace-container-limits`) ... capped per-container memory |
| hard-pinned-endpoints-108 | moonshotai/kimi-k3 | FAIL | partial | Not fixed | rogue, manually-created EndpointSlice `quote-pinned` ... pins the service to a bogus pod IP `10.244.250.17` |
| hard-silent-ledger-write-denied-105 | moonshotai/kimi-k3 | PASS | partial | Fixed, cause half-explained | The evidence points to the finance-data team's `orders-export-s3-nightly` job ... their export revokes INSERT for consistency and re-grants  |
| hard-telemetry-noise-hides-scheduling-112 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | Both worker nodes had been tainted with `dedicated=batch:NoSchedule`... when the currency pod was recreated it went `Pending` with `FailedSc |
| hard-allowlist-forgets-checkout-106 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | the new `product-catalog-allow-clients` network policy omitted checkout. Browsing remained allowed, but checkout could not retrieve product  |
| hard-cart-chained-addr-auth-103 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | it used port `6380` instead of `6379` and omitted the required authentication. |
| hard-duplicate-env-override-109 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | the recommendation Deployment contained a duplicate `PRODUCT_CATALOG_ADDR` set to `product-catalog:3550`, overriding the correct value |
| hard-egress-policy-blocks-db-102 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The `product-catalog` egress policy omitted PostgreSQL port 5432, preventing database access. |
| hard-fix-reverted-by-cronjob-101 | openai/gpt-6.1-sol | FAIL | partial | Not fixed | the latest payment deployment changed its listening port to `8081`, while the Service still routed checkout requests to `8080`. |
| hard-flag-in-source-of-truth-111 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | the `paymentFailure` feature flag was set to `50%`... setting the flag to `off` in both the persistent ConfigMap and the live flagd configur |
| hard-flag-targeting-rule-132 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | a scheduled `paymentFailure` feature-flag rule activated a **95% failure rate**... Removed the rule from the live and saved configuration an |
| hard-ghost-legacy-email-pods-104 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The `email` Service selector matched both the real email application and `email-v1-legacy`. The legacy container returned HTTP 501 |
| hard-job-sidecar-never-completes-127 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | the ledger migration succeeded, but its continuously running log-shipper container prevented the Job from completing. Accounting was stuck w |
| hard-kafka-consumer-quota-130 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | a Kafka quota limited accounting’s `rdkafka` client to **1 byte/second**, stalling order consumption |
| hard-masked-second-fault-107 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | Checkout used `product-catalog:9090`; corrected it to `product-catalog:8080`. Shipping’s Service forwarded traffic to port `8888`, but shipp |
| hard-mutating-policy-rewrites-pods-131 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The `platform-pod-defaults` admission policy changed replacement checkout pods’ payment address to `payment:8081`, but payment only listens  |
| hard-oom-fix-blocked-by-limitrange-110 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | memory limit had been reduced from 450 MiB to 48 MiB, causing repeated OOM kills. A temporary 128 MiB namespace cap also blocked restoring i |
| hard-pinned-endpoints-108 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The `quote` Service had no pod selector and used a stale, manually pinned endpoint (`10.244.250.17`), causing shipping quote requests to tim |
| hard-silent-ledger-write-denied-105 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The accounting database user lacked `INSERT` permission on `accounting."order"`. Checkouts and confirmations succeeded, but ledger writes fa |
| hard-telemetry-noise-hides-scheduling-112 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | Both worker nodes had `dedicated=batch:NoSchedule` taints, leaving the currency pod Pending with no service endpoints. Removed those taints |
| hard-allowlist-forgets-checkout-106 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | allows ingress to product-catalog only from pods labeled `opentelemetry.io/name` in `[frontend, recommendation]` — the `checkout` service wa |
| hard-cart-chained-addr-auth-103 | z-ai/glm-5.3 | PASS | missing | Fixed, cause wrong or not stated | The report is incoherent garbled text that names no object, mechanism, root cause, or fix. |
| hard-duplicate-env-override-109 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The `recommendation` Deployment had a *duplicated* `PRODUCT_CATALOG_ADDR` environment variable... a second entry — `product-catalog:3550` —  |
| hard-egress-policy-blocks-db-102 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | `product-catalog-egress-hardening` ... restricted egress ... to only DNS (53), and ports 8080/443/... but omitted the PostgreSQL port 5432 t |
| hard-fix-reverted-by-cronjob-101 | z-ai/glm-5.3 | FAIL | partial | Not fixed | accidentally changed the `PAYMENT_PORT` environment variable from `8080` to `8081`... no other workloads were touched. |
| hard-flag-in-source-of-truth-111 | z-ai/glm-5.3 | PASS | missing | Fixed, cause wrong or not stated | The report is incoherent garbled text with no identifiable object, mechanism, root cause or fix. |
| hard-flag-targeting-rule-132 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | added a time-triggered targeting rule to the `paymentFailure` flag in the `flagd-config` ConfigMap: once `flagd.timestamp >= 1792487450`...  |
| hard-ghost-legacy-email-pods-104 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | `email-v1-legacy` ... pod template *also* carried that label ... answers every POST with HTTP 501. Because both pods matched the Service sel |
| hard-job-sidecar-never-completes-127 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | the Job also included a `log-shipper` container ... as a *regular* container ... Because it never exits, the Job pod could never reach `Comp |
| hard-kafka-consumer-quota-130 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | A Kafka client-id quota (`consumer_byte_rate=1.0`, i.e. 1 byte/second) was applied to client-id `rdkafka` — the accounting service's Kafka c |
| hard-masked-second-fault-107 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | checkout deployment had PRODUCT_CATALOG_ADDR=product-catalog:9090, but the product-catalog Service exposes 8080 ... shipping Service had tar |
| hard-mutating-policy-rewrites-pods-131 | z-ai/glm-5.3 | PASS | partial | Fixed, cause half-explained | the pods were created with the bad value despite no pod-mutating webhook being visible, and deleting/recreating the pod reproduced the bad e |
| hard-oom-fix-blocked-by-limitrange-110 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The `ad` deployment's memory limit had been tuned down to 48Mi... A namespace-wide LimitRange (`namespace-container-limits`)... max 128Mi me |
| hard-pinned-endpoints-108 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The `quote` Service had its pod selector removed... hand-made EndpointSlice `quote-pinned` ... pointing at a bogus IP (`10.244.250.17`) that |
| hard-silent-ledger-write-denied-105 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | the **INSERT privilege on `accounting."order"` had been revoked** (the other tables still had it). So every order insert failed |
| hard-telemetry-noise-hides-scheduling-112 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | Both worker nodes had been tainted with `dedicated=batch:NoSchedule`... the `currency` pod ... sat `Pending` with `FailedScheduling` |

## How far to trust the judge

No human grades yet. Run: python bench/judge.py audit --suite hard-v1

Judge cost for these grades: $1.423
