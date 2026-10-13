# Diagnosis scores (hard-v1-any-version)

Judge: claude-opus-5-5, rubric v2. The judge saw only the answer key, the incident prompt and the model's written report (no model name, no PASS/FAIL). Pass rate comes from the verifier and is not affected by the judge.


| Model | Episodes | Pass rate | Root cause correct | Location correct | Mechanism correct | Diagnosis score | Fixed + understood | Fixed, cause wrong/unstated | Blamed noise | Judge votes split |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 12 | 11/12 (92%) | 12/12 (100%) | - | - | 1.00 | 11/12 | 0/12 | 0 | 0 |
| gemini-3.8-flash | 12 | 1/12 (8%) | 9/12 (75%) | - | - | 0.83 | 1/12 | 0/12 | 0 | 0 |

Diagnosis score: correct = 1, partial = 0.5, wrong or missing = 0, averaged over episodes.


## Every episode

| Scenario | Model | Verifier | Root cause | Outcome | Judge's evidence |
|---|---|---|---|---|---|
| hard-allowlist-forgets-checkout-106 | claude-opus-5-5 | PASS | correct | Fixed + understood | It only lets pods labeled `frontend` or `recommendation` reach product-catalog on port 8080. It left out `checkout` |
| hard-cart-chained-addr-auth-103 | claude-opus-5-5 | PASS | correct | Fixed + understood | the `VALKEY_ADDR` setting on the cart deployment was changed to `valkey-cart:6380`. Nothing listens on that port; the service and pod only e |
| hard-duplicate-env-override-109 | claude-opus-5-5 | PASS | correct | Fixed + understood | The recommendation deployment set the `PRODUCT_CATALOG_ADDR` environment variable twice... When a variable is listed twice, Kubernetes uses  |
| hard-egress-policy-blocks-db-102 | claude-opus-5-5 | PASS | correct | Fixed + understood | It left out Postgres port 5432, so product-catalog could no longer reach `astronomy-db`. |
| hard-fix-reverted-by-cronjob-101 | claude-opus-5-5 | PASS | correct | Fixed + understood | Every minute it uses curl against the Kubernetes API to set `PAYMENT_PORT=8081` on the payment deployment. |
| hard-flag-in-source-of-truth-111 | claude-opus-5-5 | PASS | correct | Fixed + understood | In it, the `paymentFailure` flag's default was set to `"50%"` instead of `"off"`. |
| hard-ghost-legacy-email-pods-104 | claude-opus-5-5 | PASS | correct | Fixed + understood | Its pods carried the label `opentelemetry.io/name=email`, which is exactly the label the `email` service uses to pick where to send traffic. |
| hard-masked-second-fault-107 | claude-opus-5-5 | PASS | correct | Fixed + understood | The checkout Deployment had `PRODUCT_CATALOG_ADDR=product-catalog:9090`... Its `targetPort` was `8888`, but the shipping container listens o |
| hard-oom-fix-blocked-by-limitrange-110 | claude-opus-5-5 | PASS | correct | Fixed + understood | It caps every container at 128Mi, so the old 300Mi setting would have been refused. |
| hard-pinned-endpoints-108 | claude-opus-5-5 | PASS | correct | Fixed + understood | EndpointSlice `quote-pinned` ... pointed at `10.244.250.17`, which no pod uses ... the `quote` Service also had no pod selector |
| hard-silent-ledger-write-denied-105 | claude-opus-5-5 | FAIL | correct | Understood, not fixed | Someone revoked the `INSERT` permission on the `accounting."order"` table from `astronomy_user`, the account accounting connects with. |
| hard-telemetry-noise-hides-scheduling-112 | claude-opus-5-5 | PASS | correct | Fixed + understood | add a `dedicated=batch:NoSchedule` taint to both worker nodes ... the new one couldn't be placed on any node |
| hard-allowlist-forgets-checkout-106 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | restricted ingress traffic to `product-catalog` on port 8080 to only `frontend` and `recommendation` pods |
| hard-cart-chained-addr-auth-103 | gemini-3.8-flash | FAIL | partial | Not fixed | the `VALKEY_ADDR` environment variable was incorrectly set to `valkey-cart:6380` instead of the Valkey service port `valkey-cart:6379` |
| hard-duplicate-env-override-109 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | duplicate `PRODUCT_CATALOG_ADDR` environment variable set to `product-catalog:3550`, which overrode the valid `product-catalog:8080` configu |
| hard-egress-policy-blocks-db-102 | gemini-3.8-flash | PASS | correct | Fixed + understood | restricted their egress traffic to specific ports (53, 443, 4317, 4318, 8013, 8016, 8080). It omitted port 5432, blocking outbound connectio |
| hard-fix-reverted-by-cronjob-101 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | a `payment-config-sync` CronJob was actively running every minute to enforce `PAYMENT_PORT=8081` on the payment deployment. |
| hard-flag-in-source-of-truth-111 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | the `flagd-config` ConfigMap had the `paymentFailure` feature flag configured with `"defaultVariant": "50%"` instead of `"off"` |
| hard-ghost-legacy-email-pods-104 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | The `email-v1-legacy` deployment ... had the label `opentelemetry.io/name: email` set on its pod template, matching the selector on the acti |
| hard-masked-second-fault-107 | gemini-3.8-flash | FAIL | partial | Not fixed | The `checkout` deployment was misconfigured with the environment variable `PRODUCT_CATALOG_ADDR=product-catalog:9090`. |
| hard-oom-fix-blocked-by-limitrange-110 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | a newly introduced LimitRange (`namespace-container-limits`) capped container memory across the namespace to 128Mi, preventing standard rest |
| hard-pinned-endpoints-108 | gemini-3.8-flash | FAIL | missing | Not fixed | command execution timed out before determining the internal shipping error cause or modifying cluster resources |
| hard-silent-ledger-write-denied-105 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | the database user `astronomy_user` lacked `INSERT` privileges on `accounting."order"` |
| hard-telemetry-noise-hides-scheduling-112 | gemini-3.8-flash | FAIL | correct | Understood, not fixed | the `currency` pod was stuck in `Pending` because the worker nodes were tainted with `dedicated=batch:NoSchedule` without corresponding tole |

## How far to trust the judge

You graded 24 report(s) blind. Same grade as the judge: 46%. Same correct / not-correct call: 46%. Cohen's kappa: -0.16 (above 0.6 = good, above 0.8 = very good).

Disagreements (read these reports again and decide who is right):

- hard-allowlist-forgets-checkout-106|claude-opus-5-5|1: you = partial, judge = correct
- hard-duplicate-env-override-109|claude-opus-5-5|1: you = missing, judge = correct
- hard-egress-policy-blocks-db-102|claude-opus-5-5|1: you = missing, judge = correct
- hard-fix-reverted-by-cronjob-101|claude-opus-5-5|1: you = wrong, judge = correct
- hard-flag-in-source-of-truth-111|claude-opus-5-5|1: you = partial, judge = correct
- hard-ghost-legacy-email-pods-104|claude-opus-5-5|1: you = wrong, judge = correct
- hard-masked-second-fault-107|claude-opus-5-5|1: you = partial, judge = correct
- hard-oom-fix-blocked-by-limitrange-110|claude-opus-5-5|1: you = partial, judge = correct
- hard-pinned-endpoints-108|claude-opus-5-5|1: you = missing, judge = correct
- hard-telemetry-noise-hides-scheduling-112|claude-opus-5-5|1: you = partial, judge = correct
- hard-cart-chained-addr-auth-103|gemini-3.8-flash|1: you = correct, judge = partial
- hard-masked-second-fault-107|gemini-3.8-flash|1: you = correct, judge = partial
- hard-pinned-endpoints-108|gemini-3.8-flash|1: you = correct, judge = missing

Judge cost for these grades: $0.557
