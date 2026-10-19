# Diagnosis scores (bench-v1-dev)

Judge: claude-sonnet-5-5, rubric v2. The judge saw only the answer key, the incident prompt and the model's written report (no model name, no PASS/FAIL). Pass rate comes from the verifier and is not affected by the judge.


| Model | Episodes | Pass rate | Root cause correct | Location correct | Mechanism correct | Diagnosis score | Fixed + understood | Fixed, cause wrong/unstated | Blamed noise | Judge votes split |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 20 | 20/20 (100%) | 20/20 (100%) | 20/20 | 20/20 | 1.00 | 20/20 | 0/20 | 0 | 0 |
| deepseek-v4-pro | 20 | 15/20 (75%) | 15/20 (75%) | 16/20 | 15/20 | 0.78 | 14/20 | 0/20 | 3 | 1 |

Diagnosis score: correct = 1, partial = 0.5, wrong or missing = 0, averaged over episodes.


## Every episode

| Scenario | Model | Verifier | Root cause | Outcome | Judge's evidence |
|---|---|---|---|---|---|
| catalog-fail-008 | claude-opus-5-5 | PASS | correct | Fixed + understood | The flag is called `productCatalogFailure`... Its rule checks for the Explorascope's ID, `OLJCESPC7Z`... the product catalog service deliber |
| coredns-rewrite-poison-044 | claude-opus-5-5 | PASS | correct | Fixed + understood | Someone added a rewrite rule to the cluster DNS config (the `coredns` ConfigMap in `kube-system`): rewrite name payment.default.svc.cluster. |
| flag-cart-failure-067 | claude-opus-5-5 | PASS | correct | Fixed + understood | the `cartFailure` fault-injection flag had been switched on in the live flagd flag file... `"defaultVariant": "100%"` |
| flag-image-slow-load-071 | claude-opus-5-5 | PASS | correct | Fixed + understood | A feature flag called `imageSlowLoad` was switched on to its `10sec` setting... the frontend tells the proxy... to hold each image request |
| k8s-oom-cascade-001 | claude-opus-5-5 | PASS | correct | Fixed + understood | The `cart` deployment's memory limit and request had been set to **3Mi** ... every new cart container was killed while starting ("container  |
| kafka-backlog-010 | claude-opus-5-5 | PASS | correct | Fixed + understood | `kafkaQueueProblems` was switched on in the flagd service's live flag file. While it's on, checkout sends each order to Kafka 100 times, and |
| limitrange-rejects-048 | claude-opus-5-5 | PASS | correct | Fixed + understood | a LimitRange called `container-memory-cap` ... caps every container at 128Mi ... `forbidden: maximum memory usage per Container is 128Mi, bu |
| netpol-dns-blocked-040 | claude-opus-5-5 | PASS | correct | Fixed + understood | only lets them send traffic out on TCP 8080. That also blocked DNS lookups on port 53 to CoreDNS in `kube-system`. |
| node-taint-046 | claude-opus-5-5 | PASS | correct | Fixed + understood | Both worker nodes had a `dedicated=batch:NoSchedule` taint... its replacement had nowhere to run. 3 node(s) had untolerated taint(s) |
| otel-exporter-broken-085 | claude-opus-5-5 | PASS | correct | Fixed + understood | changed the Jaeger trace exporter's address from `jaeger:4317` to `jaeger:4999`. The Jaeger service has no port 4999 |
| pg-lock-held-081 | claude-opus-5-5 | PASS | correct | Fixed + understood | A deployment called `catalog-maintenance` was locking the product table and never letting go... BEGIN; LOCK TABLE catalog.products IN ACCESS |
| pg-password-rotated-079 | claude-opus-5-5 | PASS | correct | Fixed + understood | the database maintenance changed the password for the database user `astronomy_user`, and the shop's services were still using the old one. |
| pg-revoked-grant-078 | claude-opus-5-5 | PASS | correct | Fixed + understood | the app's database user (`astronomy_user`) no longer had SELECT on the `catalog.products` table. Only `postgres` had access to it. |
| proxy-upstream-misroute-042 | claude-opus-5-5 | PASS | correct | Fixed + understood | changed one setting, `FRONTEND_PORT`, from `8080` to `8081`. The frontend service and pod only listen on port 8080, so the proxy was sending |
| wl-client-wrong-port-016 | claude-opus-5-5 | PASS | correct | Fixed + understood | changed the `checkout` deployment's `PRODUCT_CATALOG_ADDR` from `product-catalog:8080` to `product-catalog:9090`... product-catalog service  |
| wl-crash-invalid-env-013 | claude-opus-5-5 | PASS | correct | Fixed + understood | set the environment variable `SHIPPING_PORT` to the text `eighty-eighty` instead of the number `8080`... crashed on startup every time |
| wl-image-pull-011 | claude-opus-5-5 | PASS | correct | Fixed + understood | changed its image tag from `ghcr.io/open-telemetry/demo:3.1.0-currency` to `3.1.0-curency` (missing an "r"). That image doesn't exist... `Im |
| wl-listen-port-drift-014 | claude-opus-5-5 | PASS | correct | Fixed + understood | changed the `PAYMENT_PORT` setting from `8080` to `8081`, so the new payment pod listened on port 8081. Everything else still points at 8080 |
| wl-readiness-never-ready-024 | claude-opus-5-5 | PASS | correct | Fixed + understood | added a readiness check that sends a plain web request to `/healthz` on port 8080. The cart service only speaks gRPC |
| wl-unschedulable-request-017 | claude-opus-5-5 | PASS | correct | Fixed + understood | raised the container's memory request and limit from 500Mi to 64Gi. Each worker node has only about 32Gi, so the new pod couldn't be schedul |
| catalog-fail-008 | deepseek-v4-pro | FAIL | missing (votes: wrong, missing, missing) | Not fixed | I also noted `product-catalog` is running with `GOMEMLIMIT=16MiB` under a `64MiB` memory limit, which is suspicious for memory-pressure fail |
| coredns-rewrite-poison-044 | deepseek-v4-pro | FAIL | wrong | Not fixed | checkout was failing while placing orders because it could not reach the shipping quote endpoint |
| flag-cart-failure-067 | deepseek-v4-pro | FAIL | wrong | Not fixed | the cart service intermittently lost connectivity to Valkey, logging `Wasn't able to connect to redis` and returning gRPC `FailedPreconditio |
| flag-image-slow-load-071 | deepseek-v4-pro | FAIL | wrong | Not fixed | image-provider nginx's OpenTelemetry trace exporter timing out/being refused when connecting to `otel-collector:4317` |
| k8s-oom-cascade-001 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `cart` Deployment's container memory limit had been set to `3Mi`... OOM-killed during startup |
| kafka-backlog-010 | deepseek-v4-pro | PASS | correct | Fixed + understood | the feature flag `kafkaQueueProblems` was enabled... checkout service to overload the `orders` topic with duplicate messages |
| limitrange-rejects-048 | deepseek-v4-pro | PASS | correct | Fixed + understood | a `LimitRange` named `container-memory-cap` ... max container memory of `128Mi` ... its ReplicaSet could not create new pods |
| netpol-dns-blocked-040 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `frontend-egress-app-ports` NetworkPolicy selected the frontend pods and only allowed egress TCP 8080, so DNS lookups (UDP/TCP 53) from  |
| node-taint-046 | deepseek-v4-pro | PASS | correct | Fixed + understood | both worker nodes had the taint `dedicated=batch:NoSchedule`. The currency Deployment has no matching toleration, so the new pod could not b |
| otel-exporter-broken-085 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `otlp_grpc/jaeger` exporter endpoint set to `jaeger:4999`, but Jaeger only exposes OTLP gRPC on port `4317` |
| pg-lock-held-081 | deepseek-v4-pro | PASS | correct | Fixed + understood | a rogue `catalog-maintenance` Deployment was repeatedly starting PostgreSQL sessions that ran `BEGIN; LOCK TABLE catalog.products IN ACCESS  |
| pg-password-rotated-079 | deepseek-v4-pro | FAIL | correct | Understood, not fixed | the `astronomy_user` PostgreSQL role password no longer matches what the shop workloads use (`astronomy_password`) |
| pg-revoked-grant-078 | deepseek-v4-pro | PASS | correct | Fixed + understood | the role lacked `SELECT` permission on `catalog.products`. Every catalog query failed with `permission denied for table products` |
| proxy-upstream-misroute-042 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `frontend-proxy` (Envoy) deployment had `FRONTEND_PORT=8081`, but the `frontend` Service/Pod listens on `8080` |
| wl-client-wrong-port-016 | deepseek-v4-pro | PASS | correct | Fixed + understood | the checkout Deployment had `PRODUCT_CATALOG_ADDR=product-catalog:9090`, but the product-catalog Service and container actually listen on po |
| wl-crash-invalid-env-013 | deepseek-v4-pro | PASS | correct | Fixed + understood | `SHIPPING_PORT` was set to `eighty-eighty`; the shipping service parses that value as an integer port and panicked on startup |
| wl-image-pull-011 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `currency` Deployment was configured with a misspelled image tag: `ghcr.io/open-telemetry/demo:3.1.0-curency`... caused the currency pod |
| wl-listen-port-drift-014 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `payment` Deployment had `PAYMENT_PORT=8081`, so the payment service was listening on port `8081`. However, the `payment` Service ... ex |
| wl-readiness-never-ready-024 | deepseek-v4-pro | PASS | partial | Fixed, cause half-explained | latest rollout created a pod that failed its `/healthz` readiness probe (returning HTTP 400), so the cart Service had no ready endpoints |
| wl-unschedulable-request-017 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `recommendation` Deployment had its memory `requests` and `limits` changed to `64Gi`, but the cluster nodes have only ~31Gi allocatable  |

## How far to trust the judge

No human grades yet. Run: python bench/judge.py audit --suite bench-v1-dev

Judge cost for these grades: $0.430
