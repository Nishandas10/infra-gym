# Diagnosis scores (hard)

Judge: claude-opus-5-5, rubric v1. The judge saw only the answer key, the incident prompt and the model's written report (no model name, no PASS/FAIL). Pass rate comes from the verifier and is not affected by the judge.


| Model | Episodes | Pass rate | Root cause correct | Diagnosis score | Fixed + understood | Fixed, cause wrong/unstated | Blamed noise | Judge votes split |
|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 12 | 11/12 (92%) | 12/12 (100%) | 1.00 | 11/12 | 0/12 | 0 | 0 |

Diagnosis score: correct = 1, partial = 0.5, wrong or missing = 0, averaged over episodes.


## Every episode

| Scenario | Model | Verifier | Root cause | Outcome | Judge's evidence |
|---|---|---|---|---|---|
| hard-allowlist-forgets-checkout-106 | claude-opus-5-5 | PASS | correct | Fixed + understood | It only lets pods labeled `frontend` or `recommendation` reach product-catalog on port 8080. It left out `checkout` |
| hard-cart-chained-addr-auth-103 | claude-opus-5-5 | PASS | correct | Fixed + understood | the `VALKEY_ADDR` setting on the cart deployment was changed to `valkey-cart:6380`. Nothing listens on that port |
| hard-duplicate-env-override-109 | claude-opus-5-5 | PASS | correct | Fixed + understood | When a variable is listed twice, Kubernetes uses the last value. So the service was dialing product-catalog on port 3550, but that service o |
| hard-egress-policy-blocks-db-102 | claude-opus-5-5 | PASS | correct | Fixed + understood | It left out Postgres port 5432, so product-catalog could no longer reach `astronomy-db`. |
| hard-fix-reverted-by-cronjob-101 | claude-opus-5-5 | PASS | correct | Fixed + understood | Every minute it uses curl against the Kubernetes API to set `PAYMENT_PORT=8081` on the payment deployment. |
| hard-flag-in-source-of-truth-111 | claude-opus-5-5 | PASS | correct | Fixed + understood | In it, the `paymentFailure` flag's default was set to `"50%"` instead of `"off"`. |
| hard-ghost-legacy-email-pods-104 | claude-opus-5-5 | PASS | correct | Fixed + understood | Its pods carried the label `opentelemetry.io/name=email`, which is exactly the label the `email` service uses to pick where to send traffic. |
| hard-masked-second-fault-107 | claude-opus-5-5 | PASS | correct | Fixed + understood | The checkout Deployment had `PRODUCT_CATALOG_ADDR=product-catalog:9090`... Its `targetPort` was `8888`, but the shipping container listens o |
| hard-oom-fix-blocked-by-limitrange-110 | claude-opus-5-5 | PASS | correct | Fixed + understood | It caps every container at 128Mi, so the old 300Mi setting would have been refused. |
| hard-pinned-endpoints-108 | claude-opus-5-5 | PASS | correct | Fixed + understood | EndpointSlice `quote-pinned`... pointed at `10.244.250.17`, which no pod uses... the `quote` Service also had no pod selector |
| hard-silent-ledger-write-denied-105 | claude-opus-5-5 | FAIL | correct | Understood, not fixed | Someone revoked the `INSERT` permission on the `accounting."order"` table from `astronomy_user`, the account accounting connects with. |
| hard-telemetry-noise-hides-scheduling-112 | claude-opus-5-5 | PASS | correct | Fixed + understood | someone used `kubectl patch` to add a `dedicated=batch:NoSchedule` taint to both worker nodes... the new one couldn't be placed on any node |

## How far to trust the judge

You graded 12 report(s) blind. Same grade as the judge: 17%. Same correct / not-correct call: 17%. Cohen's kappa: 0.00 (above 0.6 = good, above 0.8 = very good).

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

Judge cost for these grades: $0.268
