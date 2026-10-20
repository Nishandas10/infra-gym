# Diagnosis scores (bench-v1-dev)

Judge: claude-sonnet-5-5, rubric v2. The judge saw only the answer key, the incident prompt and the model's written report (no model name, no PASS/FAIL). Pass rate comes from the verifier and is not affected by the judge.


| Model | Episodes | Pass rate | Root cause correct | Location correct | Mechanism correct | Diagnosis score | Fixed + understood | Fixed, cause wrong/unstated | Blamed noise | Judge votes split |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 20 | 20/20 (100%) | 20/20 (100%) | 20/20 | 20/20 | 1.00 | 20/20 | 0/20 | 0 | 0 |
| claude-sonnet-5-5 | 20 | 18/20 (90%) | 18/20 (90%) | 18/20 | 17/20 | 0.90 | 18/20 | 0/20 | 1 | 0 |
| deepseek-v4-pro | 21 | 16/21 (76%) | 16/21 (76%) | 17/21 | 16/21 | 0.79 | 15/21 | 0/21 | 3 | 1 |
| gemini-4-argon | 20 | 20/20 (100%) | 20/20 (100%) | 20/20 | 20/20 | 1.00 | 20/20 | 0/20 | 0 | 0 |
| moonshotai/kimi-k3 | 20 | 17/20 (85%) | 18/20 (90%) | 18/20 | 16/20 | 0.90 | 17/20 | 0/20 | 0 | 0 |
| openai/gpt-6.1-sol | 20 | 19/20 (95%) | 19/20 (95%) | 17/20 | 19/20 | 0.95 | 19/20 | 0/20 | 1 | 0 |
| z-ai/glm-5.3 | 20 | 17/20 (85%) | 18/20 (90%) | 18/20 | 18/20 | 0.90 | 17/20 | 0/20 | 0 | 0 |

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
| catalog-fail-008 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | the targeting rule for `productCatalogFailure` returned `"on"` for product `OLJCESPC7Z`... product-catalog service then threw `Product Catal |
| coredns-rewrite-poison-044 | claude-sonnet-5-5 | FAIL | missing | Not fixed | I found nothing broken and changed nothing. |
| flag-cart-failure-067 | claude-sonnet-5-5 | FAIL | wrong | Not fixed | all the failure-injection flags in `flagd-config` are `off`. That includes `cartFailure` |
| flag-image-slow-load-071 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | product images were slow because the `imageSlowLoad` feature flag was set to `10sec` in flagd |
| k8s-oom-cascade-001 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `cart` deployment had a memory limit and request of **3Mi**. The .NET cart container can't start in that, so it was OOM-killed. |
| kafka-backlog-010 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | `kafkaQueueProblems` set to `defaultVariant: "on"`... floods Kafka with orders and makes the consumer sleep... re-consuming the same order I |
| limitrange-rejects-048 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | A LimitRange named `container-memory-cap` ... capped every container's memory limit at 128Mi. The `ad` deployment asks for a 450Mi limit, so |
| netpol-dns-blocked-040 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | restricts their egress to TCP 8080 only. That blocked DNS lookups to CoreDNS on port 53. |
| node-taint-046 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | Both worker nodes carry the taint `dedicated=batch:NoSchedule`... The replacement currency pod had no matching toleration, so it sat in `Pen |
| otel-exporter-broken-085 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `otel-collector-agent` ConfigMap sent traces to Jaeger at `jaeger:4999`. The `jaeger` Service and pod only listen for OTLP/gRPC on 4317. |
| pg-lock-held-081 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | `catalog-maintenance` ran `LOCK TABLE catalog.products IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(86400)` against `astronomy-db` in a loop. E |
| pg-password-rotated-079 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | left the `astronomy_user` role in `astronomy-db` with a password that no longer matched the one the apps use |
| pg-revoked-grant-078 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `astronomy_user` database role had lost its SELECT privilege on `catalog.products` in `astronomy-db`. Every product lookup failed with ` |
| proxy-upstream-misroute-042 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | `frontend-proxy` had `FRONTEND_PORT=8081`, but the `frontend` service and pod listen on 8080. Envoy couldn't reach its shop upstream |
| wl-client-wrong-port-016 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The checkout deployment had `PRODUCT_CATALOG_ADDR=product-catalog:9090`. The `product-catalog` service and pod listen on 8080 |
| wl-crash-invalid-env-013 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `shipping` deployment had `SHIPPING_PORT` set to `eighty-eighty`, which isn't a number. The service panicked at startup |
| wl-image-pull-011 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | the `currency` deployment was pointing at `ghcr.io/open-telemetry/demo:3.1.0-curency`, which is missing an "r". The image doesn't exist, so  |
| wl-listen-port-drift-014 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `payment` Deployment (revision 47) had `PAYMENT_PORT=8081`. The payment gRPC server therefore listened on 8081. The Service `payment`... |
| wl-readiness-never-ready-024 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | the `cart` deployment's readiness probe had been changed to an HTTP GET on `/healthz`. The cart service speaks gRPC... never became Ready, a |
| wl-unschedulable-request-017 | claude-sonnet-5-5 | PASS | correct | Fixed + understood | The `recommendation` deployment's latest revision (85) set its memory request and limit to 64Gi... nodes only have about 32Gi each, so no ne |
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
| pg-revoked-grant-078 | deepseek-v4-pro | PASS | correct | Fixed + understood | `astronomy_user` had lost (or was missing) `SELECT` permission on `catalog.products`, so every product query failed with: ERROR: permission  |
| proxy-upstream-misroute-042 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `frontend-proxy` (Envoy) deployment had `FRONTEND_PORT=8081`, but the `frontend` Service/Pod listens on `8080` |
| wl-client-wrong-port-016 | deepseek-v4-pro | PASS | correct | Fixed + understood | the checkout Deployment had `PRODUCT_CATALOG_ADDR=product-catalog:9090`, but the product-catalog Service and container actually listen on po |
| wl-crash-invalid-env-013 | deepseek-v4-pro | PASS | correct | Fixed + understood | `SHIPPING_PORT` was set to `eighty-eighty`; the shipping service parses that value as an integer port and panicked on startup |
| wl-image-pull-011 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `currency` Deployment was configured with a misspelled image tag: `ghcr.io/open-telemetry/demo:3.1.0-curency`... caused the currency pod |
| wl-listen-port-drift-014 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `payment` Deployment had `PAYMENT_PORT=8081`, so the payment service was listening on port `8081`. However, the `payment` Service ... ex |
| wl-readiness-never-ready-024 | deepseek-v4-pro | PASS | partial | Fixed, cause half-explained | latest rollout created a pod that failed its `/healthz` readiness probe (returning HTTP 400), so the cart Service had no ready endpoints |
| wl-unschedulable-request-017 | deepseek-v4-pro | PASS | correct | Fixed + understood | the `recommendation` Deployment had its memory `requests` and `limits` changed to `64Gi`, but the cluster nodes have only ~31Gi allocatable  |
| catalog-fail-008 | gemini-4-argon | PASS | correct | Fixed + understood | the `productCatalogFailure` feature flag targeting rule was enabled (`"on"`) specifically when `product_id == "OLJCESPC7Z"` |
| coredns-rewrite-poison-044 | gemini-4-argon | PASS | correct | Fixed + understood | The `coredns` ConfigMap in the `kube-system` namespace had a misconfigured DNS rewrite rule: rewrite name payment.default.svc.cluster.local  |
| flag-cart-failure-067 | gemini-4-argon | PASS | correct | Fixed + understood | had the `cartFailure` feature flag set to `"defaultVariant": "100%"`... the `cart` service simulated a Redis connection failure |
| flag-image-slow-load-071 | gemini-4-argon | PASS | correct | Fixed + understood | The `imageSlowLoad` feature flag in the `flagd` pod's runtime configuration file ... was set to `"defaultVariant": "10sec"` (`10000` ms), in |
| k8s-oom-cascade-001 | gemini-4-argon | PASS | correct | Fixed + understood | The `cart` Deployment in namespace `default` was updated with a memory limit and request of `3Mi` ... container init was OOM-killed |
| kafka-backlog-010 | gemini-4-argon | PASS | correct | Fixed + understood | kafkaQueueProblems feature flag was set to "defaultVariant": "on"... causes checkout to flood the Kafka orders topic with duplicate order me |
| limitrange-rejects-048 | gemini-4-argon | PASS | correct | Fixed + understood | LimitRange named `container-memory-cap` ... maximum container memory limit of `128Mi` ... admission controller rejected new pod creation whe |
| netpol-dns-blocked-040 | gemini-4-argon | PASS | correct | Fixed + understood | only permitted outbound TCP traffic on port `8080`... DNS queries to `kube-dns`/CoreDNS on port `53` (UDP/TCP) ... were blocked |
| node-taint-046 | gemini-4-argon | PASS | correct | Fixed + understood | Both worker nodes ... had been tainted with `dedicated=batch:NoSchedule` ... The replacement pod did not tolerate `dedicated=batch:NoSchedul |
| otel-exporter-broken-085 | gemini-4-argon | PASS | correct | Fixed + understood | `otlp_grpc/jaeger` exporter ... misconfigured with `endpoint: jaeger:4999`. However, the `jaeger` Service ... listen for OTLP gRPC traffic o |
| pg-lock-held-081 | gemini-4-argon | PASS | correct | Fixed + understood | catalog-maintenance Deployment ... held an ACCESS EXCLUSIVE lock on catalog.products (BEGIN; LOCK TABLE catalog.products IN ACCESS EXCLUSIVE |
| pg-password-rotated-079 | gemini-4-argon | PASS | correct | Fixed + understood | the password for the PostgreSQL role `astronomy_user` in `astronomy-db` was changed in-place ... while ... `product-catalog` and `accounting |
| pg-revoked-grant-078 | gemini-4-argon | PASS | correct | Fixed + understood | REVOKE SELECT ON catalog.products FROM astronomy_user had been applied. As a result, product-catalog queries failed with ERROR: permission d |
| proxy-upstream-misroute-042 | gemini-4-argon | PASS | correct | Fixed + understood | the `FRONTEND_PORT` environment variable was misconfigured to `8081` instead of `8080`. Because the `frontend` service and pod listen on por |
| wl-client-wrong-port-016 | gemini-4-argon | PASS | correct | Fixed + understood | The `checkout` deployment had its `PRODUCT_CATALOG_ADDR` environment variable misconfigured as `product-catalog:9090`, whereas the `product- |
| wl-crash-invalid-env-013 | gemini-4-argon | PASS | correct | Fixed + understood | The `shipping` Deployment had its `SHIPPING_PORT` environment variable misconfigured as "eighty-eighty" instead of "8080". This caused the ` |
| wl-image-pull-011 | gemini-4-argon | PASS | correct | Fixed + understood | patched with a misspelled container image (`ghcr.io/open-telemetry/demo:3.1.0-curency` instead of `...3.1.0-currency`) ... replacement pod e |
| wl-listen-port-drift-014 | gemini-4-argon | PASS | correct | Fixed + understood | `PAYMENT_PORT` environment variable was misconfigured to `8081`... payment Service (`targetPort: 8080`) expected traffic on port `8080`, res |
| wl-readiness-never-ready-024 | gemini-4-argon | PASS | correct | Fixed + understood | The `cart` Deployment had an `httpGet` readiness probe configured on `http://:8080/healthz`. However, the `cart` service is an ASP.NET Core  |
| wl-unschedulable-request-017 | gemini-4-argon | PASS | correct | Fixed + understood | The `recommendation` Deployment was updated with an excessive memory request and limit (`64Gi`, exceeding the ~32Gi capacity of each cluster |
| catalog-fail-008 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The OpenFeature flag `productCatalogFailure` was active... makes the `product-catalog` service return a gRPC `INTERNAL` error ... specifical |
| coredns-rewrite-poison-044 | moonshotai/kimi-k3 | FAIL | wrong | Not fixed | The kube-proxy pod on node `ai-gym-worker` had lost (or never programmed) the iptables DNAT rules for the checkout service |
| flag-cart-failure-067 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The `cartFailure` chaos feature flag in flagd had been switched at runtime from `off` to `100%`. With that flag on, the cart service deliber |
| flag-image-slow-load-071 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The demo's feature flag `imageSlowLoad` ... was enabled at runtime with variant `10sec` (10000 ms) ... causing the frontend to delay product |
| k8s-oom-cascade-001 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The `cart` deployment's container memory limit had been changed to **3Mi** ... container init was OOM-killed (memory limit too low?) |
| kafka-backlog-010 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The OpenFeature flag `kafkaQueueProblems` was enabled in flagd's live flag file ... With this flag on, the fraud-detection consumer sleeps 1 |
| limitrange-rejects-048 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | A LimitRange named `container-memory-cap` ... capping memory at **128Mi max per container** ... replacement pods ... were rejected by the AP |
| netpol-dns-blocked-040 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | allowed egress only on TCP port 8080 — with no allowance for DNS (UDP/TCP 53 to kube-dns). As a result, the Next.js frontend could no longer |
| node-taint-046 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | Both worker nodes had been tainted with `dedicated=batch:NoSchedule`, but no workload anywhere in the cluster carries a matching toleration. |
| otel-exporter-broken-085 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The `otel-collector-agent` ConfigMap's traces exporter `otlp_grpc/jaeger` had been pointed at a non-existent endpoint, `jaeger:4999`. |
| pg-lock-held-081 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | catalog-maintenance deployment... LOCK TABLE catalog.products IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(86400)... every product-catalog quer |
| pg-password-rotated-079 | moonshotai/kimi-k3 | FAIL | wrong | Not fixed | service traffic is being delivered to a backend that rejects the valid credentials, i.e. stale service routing/endpoints (kube-proxy/iptable |
| pg-revoked-grant-078 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | the application role `astronomy_user` had lost its `SELECT` privilege on `catalog.products` ... failed with `permission denied for table pro |
| proxy-upstream-misroute-042 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | frontend-proxy (Envoy) Deployment... FRONTEND_PORT env var pointed to 8081, while the frontend Service/pods actually listen on 8080 |
| wl-client-wrong-port-016 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The `checkout` deployment had a misconfigured environment variable: `PRODUCT_CATALOG_ADDR=product-catalog:9090`. The `product-catalog` servi |
| wl-crash-invalid-env-013 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | `SHIPPING_PORT` environment variable set to the non-numeric string `eighty-eighty`. The Rust shipping service panicked at startup |
| wl-image-pull-011 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The `currency` Deployment was pointing at a non-existent image due to a typo in the tag: `ghcr.io/open-telemetry/demo:3.1.0-curency` |
| wl-listen-port-drift-014 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | The `payment` Deployment had been changed to set `PAYMENT_PORT=8081`... the `payment` Service still routed traffic to `targetPort: 8080`. |
| wl-readiness-never-ready-024 | moonshotai/kimi-k3 | FAIL | correct | Understood, not fixed | add an HTTP/1.1 `httpGet` readiness probe on `/healthz:8080` ... doesn't even map a `/healthz` route, so the probe got 400/404, the pod neve |
| wl-unschedulable-request-017 | moonshotai/kimi-k3 | PASS | correct | Fixed + understood | its pod template's memory request/limit was set to **64Gi** (revision 91). The cluster nodes only have ~31Gi each, so the replacement pod wa |
| catalog-fail-008 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | the live `productCatalogFailure` flag was set to inject errors specifically for product `OLJCESPC7Z` ... causing HTTP 500 responses |
| coredns-rewrite-poison-044 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | A CoreDNS rewrite incorrectly resolved `payment` to the shipping service, sending gRPC payment requests to an HTTP/1.1 endpoint. |
| flag-cart-failure-067 | openai/gpt-6.1-sol | FAIL | wrong | Not fixed | A failed cart rollout referenced the missing Secret `valkey-cart-credentials`. |
| flag-image-slow-load-071 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The live `imageSlowLoad` feature flag was set to `10sec`, causing the frontend to request an intentional 10-second delay for product images. |
| k8s-oom-cascade-001 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The cart deployment’s memory request and limit had been reduced to **3 MiB**, leaving the cart service without healthy endpoints. |
| kafka-backlog-010 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The live `kafkaQueueProblems` fault-injection flag was enabled, flooding Kafka with duplicate order events and adding a one-second delay per |
| limitrange-rejects-048 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | A newly added `LimitRange` in `default` capped container memory at 128 MiB... Kubernetes rejected its replacement pod after the restart. |
| netpol-dns-blocked-040 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | the frontend’s egress NetworkPolicy allowed only TCP port 8080, blocking DNS and preventing backend service-name resolution |
| node-taint-046 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | both worker nodes had a `dedicated=batch:NoSchedule` taint, but currency lacked the matching toleration |
| otel-exporter-broken-085 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The OpenTelemetry collectors were configured to export traces to `jaeger:4999`, but Jaeger listens for OTLP gRPC on port `4317`. |
| pg-lock-held-081 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The `catalog-maintenance` pod held an exclusive lock on `catalog.products` while sleeping for 24 hours, blocking catalog access. |
| pg-password-rotated-079 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The database password for `astronomy_user` no longer matched the credentials configured in the product catalog and accounting services |
| pg-revoked-grant-078 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The catalog’s database user was missing `SELECT` permission on `catalog.products`, causing repeated database permission errors. |
| proxy-upstream-misroute-042 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | `frontend-proxy` routed storefront requests to `frontend:8081`, but the frontend listens on port `8080`... Fixed the proxy's `FRONTEND_PORT` |
| wl-client-wrong-port-016 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | Checkout pointed to `product-catalog:9090`, but the catalog serves on port `8080`. This caused product lookups during order placement to fai |
| wl-crash-invalid-env-013 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | Shipping was crashing because `SHIPPING_PORT` was set to `eighty-eighty`, causing a port-parsing error. |
| wl-image-pull-011 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The currency deployment used a misspelled image tag, `3.1.0-curency`, causing `ImagePullBackOff`. |
| wl-listen-port-drift-014 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | Payment was configured to listen on port `8081`, while its Kubernetes Service and checkout expected `8080`, causing connection refusals. |
| wl-readiness-never-ready-024 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The cart’s readiness probe used HTTP `/healthz` on a gRPC-only port... Kubernetes marked the cart unready and removed its service endpoint |
| wl-unschedulable-request-017 | openai/gpt-6.1-sol | PASS | correct | Fixed + understood | The recommendation deployment requested **64 GiB of memory per pod**, exceeding every node’s capacity. Its replacement pod could not schedul |
| catalog-fail-008 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | flagd feature flag `productCatalogFailure` had a targeting rule evaluating to "on" for that specific product ID |
| coredns-rewrite-poison-044 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | `rewrite name payment.default.svc.cluster.local shipping.default.svc.cluster.local` rule had been injected into the CoreDNS Corefile (kube-s |
| flag-cart-failure-067 | z-ai/glm-5.3 | FAIL | wrong | Not fixed | A bad rollout of the `cart` Deployment ... had mangled the `VALKEY_ADDR` environment variable to `valkey-cart:6379,password=$(VALKEY_PASSWOR |
| flag-image-slow-load-071 | z-ai/glm-5.3 | FAIL | missing | Not fixed | I could not confirm one — my investigation found no evidence of the reported 10-second delay. |
| k8s-oom-cascade-001 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The `cart` Deployment's latest revision (121) had its container memory limit/requests set to an absurdly low `3Mi`... OOM-killed during cont |
| kafka-backlog-010 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The feature flag `kafkaQueueProblems` had been turned **on** ... checkout flooded Kafka with duplicate order messages, and fraud-detection a |
| limitrange-rejects-048 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | A `LimitRange` named `container-memory-cap` ... setting a maximum of 128Mi memory per container ... API server rejected every pod ... maximu |
| netpol-dns-blocked-040 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | NetworkPolicy named `frontend-egress-app-ports`... allowed only TCP port 8080. This silently blocked the frontend's DNS traffic (UDP/TCP 53  |
| node-taint-046 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | both worker nodes carried a `dedicated=batch:NoSchedule` taint that the pod (and no other shop workload) tolerates |
| otel-exporter-broken-085 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | ConfigMap `otel-collector-agent`... `otlp_grpc/jaeger: endpoint: jaeger:4999`. Port 4999 doesn't exist |
| pg-lock-held-081 | z-ai/glm-5.3 | FAIL | correct | Understood, not fixed | `catalog-maintenance` Deployment ... took an `ACCESS EXCLUSIVE` lock on the `catalog.products` table, holding it for 24 hours (`pg_sleep(864 |
| pg-password-rotated-079 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | the password of the `astronomy_user` Postgres account inside `astronomy-db` was changed, while ... `product-catalog`, `accounting` still aut |
| pg-revoked-grant-078 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The application role `astronomy_user` had no privileges on the `catalog` schema / `catalog.products` table ... `pq: permission denied for ta |
| proxy-upstream-misroute-042 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | changed the `frontend-proxy` Deployment's `FRONTEND_PORT` environment variable to `8081`... Envoy therefore tried to connect to `frontend:80 |
| wl-client-wrong-port-016 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | `PRODUCT_CATALOG_ADDR=product-catalog:9090`, while the `product-catalog` Service actually listens on port **8080** |
| wl-crash-invalid-env-013 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The shipping Deployment had a misconfigured environment variable — `SHIPPING_PORT` was set to the string "eighty-eighty" instead of `8080`. |
| wl-image-pull-011 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The `currency` Deployment had a typo in its image tag — `ghcr.io/open-telemetry/demo:3.1.0-curency`... pod was stuck in `ErrImagePull`/`Imag |
| wl-listen-port-drift-014 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | The `payment` Deployment had the environment variable `PAYMENT_PORT` set to `8081`... Service exposes port 8080... server started listening  |
| wl-readiness-never-ready-024 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | added an HTTP `readinessProbe` (`httpGet /healthz:8080`) to the cart container... pod never became Ready; with no ready endpoints behind the |
| wl-unschedulable-request-017 | z-ai/glm-5.3 | PASS | correct | Fixed + understood | requests: memory=64Gi / limits: memory=64Gi ... the new pod could never be scheduled — no node can satisfy a 64Gi request |

## How far to trust the judge

No human grades yet. Run: python bench/judge.py audit --suite bench-v1-dev

Judge cost for these grades: $1.489
