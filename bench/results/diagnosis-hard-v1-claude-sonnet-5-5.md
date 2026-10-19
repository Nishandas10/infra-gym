# Diagnosis scores (hard-v1)

Judge: claude-sonnet-5-5, rubric v2. The judge saw only the answer key, the incident prompt and the model's written report (no model name, no PASS/FAIL). Pass rate comes from the verifier and is not affected by the judge.


| Model | Episodes | Pass rate | Root cause correct | Location correct | Mechanism correct | Diagnosis score | Fixed + understood | Fixed, cause wrong/unstated | Blamed noise | Judge votes split |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 24 | 23/24 (96%) | 22/24 (92%) | 23/24 | 22/24 | 0.94 | 22/24 | 0/24 | 0 | 0 |
| deepseek-v4-pro | 16 | 12/16 (75%) | 12/16 (75%) | 12/16 | 12/16 | 0.81 | 12/16 | 0/16 | 0 | 0 |

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

## How far to trust the judge

No human grades yet. Run: python bench/judge.py audit --suite hard-v1

Judge cost for these grades: $0.482
