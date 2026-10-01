# Scenario catalog

83 scenarios, each a distinct root-cause mechanism (83 validated end to end on the live cluster).

| family | scenarios | validated | median detect | median recover |
|---|---|---|---|---|
| application | 13 | 13 | 14s | 3s |
| chaos | 12 | 12 | 20s | 3s |
| compound | 3 | 3 | 7s | 2s |
| datastore | 9 | 9 | 2s | 1s |
| observability | 6 | 6 | 26s | 14s |
| platform | 9 | 9 | 2s | 3s |
| service-network | 8 | 8 | 22s | 12s |
| workload | 23 | 23 | 2s | 18s |

Detect = time from injection until the verifier fails; recover = time from running the reference solution until it passes again.

Uniqueness rule: a scenario counts only if its root-cause mechanism differs from every other one. Changing only numbers (memory size, latency, percentages), names or random seeds makes a variant, not a new scenario, so variants are not listed here.

Validation = baseline healthy -> inject -> verifier FAIL -> still FAIL for a do-nothing agent -> reference solution -> verifier PASS -> exact restore (see `scripts/validate_scenario.py`).

| id | family | mechanism | title | validation |
|---|---|---|---|---|
| `cache-leak-009` | application | `app-flag/recommendation-cache-leak` | Recommendation cache leaks memory until OOM (recommendationCacheFailure) | VALIDATED |
| `catalog-fail-008` | application | `app-flag/catalog-single-product-failure` | One product always fails (productCatalogFailure) | VALIDATED |
| `flag-ad-failure-064` | application | `app-flag/ad-failure` | Ad service fails every request (feature flag adFailure) | VALIDATED |
| `flag-ad-high-cpu-065` | application | `app-flag/ad-high-cpu` | Ad service burns CPU on every request (adHighCpu) | VALIDATED |
| `flag-ad-manual-gc-066` | application | `app-flag/ad-full-gc` | Ad service triggers full garbage collections (adManualGc) | VALIDATED |
| `flag-cart-failure-067` | application | `app-flag/cart-failure` | Cart service errors (cartFailure) | VALIDATED |
| `flag-email-memory-leak-068` | application | `app-flag/email-memory-leak` | Email service leaks memory until it is OOMKilled (emailMemoryLeak) | VALIDATED |
| `flag-flood-homepage-073` | application | `app-flag/traffic-flood` | Synthetic traffic flood against the homepage (loadGeneratorFloodHomepage) | VALIDATED |
| `flag-image-slow-load-071` | application | `app-flag/image-slow-load` | Images served with an artificial delay (imageSlowLoad) | VALIDATED |
| `flag-intl-shipping-slow-072` | application | `app-flag/intl-shipping-slowdown` | International shipping quotes delayed (intlShippingSlowdown) | VALIDATED |
| `kafka-backlog-010` | application | `app-flag/kafka-queue-overload` | Kafka flooded and consumers slowed (kafkaQueueProblems) | VALIDATED |
| `pay-fail-006` | application | `app-flag/payment-failure` | Payment service rejects every charge (paymentFailure) | VALIDATED |
| `pay-unreachable-007` | application | `app-flag/payment-unreachable` | Checkout calls payment at a dead address (paymentUnreachable) | VALIDATED |
| `cpu-stress-004` | chaos | `chaos/cpu-stress` | CPU stressor running inside a container | VALIDATED |
| `dns-error-005` | chaos | `chaos/dns-error` | DNS lookups of one dependency fail from one service | VALIDATED |
| `dns-random-057` | chaos | `chaos/dns-wrong-answers` | DNS returns random addresses for one name | VALIDATED |
| `http-abort-058` | chaos | `chaos/http-fault-abort` | HTTP requests to a service aborted at layer 7 | VALIDATED |
| `http-replace-059` | chaos | `chaos/http-response-corruption` | HTTP responses from a service replaced with garbage | VALIDATED |
| `jvm-exception-062` | chaos | `chaos/jvm-method-exception` | Exception injected into a JVM method at runtime | VALIDATED |
| `net-bandwidth-053` | chaos | `chaos/network-bandwidth-limit` | Bandwidth throttled to a trickle on the image server | VALIDATED |
| `net-delay-002` | chaos | `chaos/network-latency` | Network latency injected on one service | VALIDATED |
| `net-packet-loss-052` | chaos | `chaos/network-packet-loss` | Heavy packet loss on a service's network interface | VALIDATED |
| `net-partition-054` | chaos | `chaos/network-partition` | Network partition between two specific services | VALIDATED |
| `pod-failure-055` | chaos | `chaos/pod-failure` | Pod stays 'Running' but its process has been replaced by a pause container | VALIDATED |
| `pod-kill-003` | chaos | `chaos/pod-kill-periodic` | A service's pod is killed every 45 seconds | VALIDATED |
| `compound-quota-blocks-fix-090` | compound | `compound/fix-blocked-by-quota` | Broken config plus a quota that blocks the rollout of the fix | VALIDATED |
| `compound-red-herring-092` | compound | `compound/red-herring` | A loud but irrelevant failing pod next to the real, quieter fault | VALIDATED |
| `compound-two-faults-091` | compound | `compound/independent-simultaneous-faults` | Two unrelated faults at the same time | VALIDATED |
| `kafka-broker-down-083` | datastore | `datastore/message-broker-down` | Message broker scaled to zero (async pipeline stops silently) | VALIDATED |
| `kafka-message-too-large-082` | datastore | `datastore/queue-message-size-limit` | Topic max message size below the size of real messages | VALIDATED |
| `pg-connection-limit-080` | datastore | `datastore/db-connection-limit` | Role connection limit set to zero | VALIDATED |
| `pg-lock-held-081` | datastore | `datastore/db-lock-held` | A stuck maintenance job holds an exclusive table lock | VALIDATED |
| `pg-password-rotated-079` | datastore | `datastore/db-credential-rotation` | Database password rotated without updating the clients | VALIDATED |
| `pg-revoked-grant-078` | datastore | `datastore/db-permission-revoked` | Database role lost SELECT on the table the service reads | VALIDATED |
| `valkey-client-pause-077` | datastore | `datastore/kv-clients-paused` | Valkey clients paused -> writes hang | VALIDATED |
| `valkey-maxmemory-075` | datastore | `datastore/kv-memory-cap-noeviction` | Valkey memory cap reached with 'noeviction' -> writes rejected | VALIDATED |
| `valkey-requirepass-076` | datastore | `datastore/kv-credential-mismatch` | Valkey password set; the client does not know it | VALIDATED |
| `grafana-datasource-089` | observability | `observability/dashboard-datasource-misconfigured` | Grafana's Prometheus datasource points at the wrong port | VALIDATED |
| `obs-pii-redaction-removed-069` | observability | `observability/telemetry-redaction-removed` | PII reaches the tracing backend after the redaction step was removed from the pipeline | VALIDATED |
| `otel-collector-unscheduled-086` | observability | `observability/collector-not-running` | Collector DaemonSet has a nodeSelector that matches no node | VALIDATED |
| `otel-exporter-broken-085` | observability | `observability/collector-exporter-misconfigured` | Collector exports traces to the wrong port | VALIDATED |
| `otel-service-endpoint-087` | observability | `observability/service-exporter-misconfigured` | One service exports telemetry to a collector name that does not exist | VALIDATED |
| `prometheus-otlp-disabled-088` | observability | `observability/metrics-ingest-disabled` | Prometheus restarted without its OTLP receiver | VALIDATED |
| `coredns-down-043` | platform | `platform/cluster-dns-down` | Cluster DNS scaled to zero | VALIDATED |
| `coredns-rewrite-poison-044` | platform | `platform/cluster-dns-rewrite` | CoreDNS rewrite rule sends one service's name to another | VALIDATED |
| `kube-proxy-stopped-051` | platform | `platform/service-proxy-down` | kube-proxy removed; Service rules go stale when a pod moves | VALIDATED |
| `limitrange-rejects-048` | platform | `platform/limit-range-rejects` | LimitRange max is lower than a container's limit | VALIDATED |
| `node-cordoned-045` | platform | `platform/nodes-cordoned` | All worker nodes cordoned; a pod cannot be rescheduled | VALIDATED |
| `node-taint-046` | platform | `platform/nodes-tainted` | Worker nodes tainted; the replacement pod has no toleration | VALIDATED |
| `pod-security-restricted-049` | platform | `platform/pod-security-admission` | Namespace switched to the 'restricted' Pod Security Standard | VALIDATED |
| `quota-blocks-pods-047` | platform | `platform/resource-quota-exhausted` | ResourceQuota lower than the namespace's pod count | VALIDATED |
| `webhook-blocks-pods-050` | platform | `platform/admission-webhook-unavailable` | Validating webhook with failurePolicy=Fail and no backend | VALIDATED |
| `netpol-default-deny-041` | service-network | `network-policy/namespace-default-deny` | Namespace-wide default-deny ingress policy | VALIDATED |
| `netpol-dns-blocked-040` | service-network | `network-policy/dns-egress-blocked` | Egress policy allows app ports but blocks DNS | VALIDATED |
| `netpol-egress-lockdown-039` | service-network | `network-policy/egress-deny` | Egress policy lets a service reach nothing but DNS | VALIDATED |
| `netpol-ingress-deny-038` | service-network | `network-policy/ingress-deny` | NetworkPolicy blocks all traffic into a service | VALIDATED |
| `proxy-upstream-misroute-042` | service-network | `edge-proxy/upstream-misconfigured` | Edge proxy routes shop traffic to the wrong upstream port | VALIDATED |
| `svc-deleted-037` | service-network | `service/deleted` | Service object deleted | VALIDATED |
| `svc-selector-mismatch-035` | service-network | `service/selector-mismatch` | Service selector matches no pods -> no endpoints | VALIDATED |
| `svc-targetport-mismatch-036` | service-network | `service/target-port-mismatch` | Service targetPort points at a port nothing listens on | VALIDATED |
| `k8s-oom-cascade-001` | workload | `workload/oom-memory-limit` | Memory limit far below what the service needs -> OOMKilled / CrashLoopBackOff | VALIDATED |
| `wl-bad-command-012` | workload | `workload/bad-entrypoint` | Container command points at a binary that does not exist | VALIDATED |
| `wl-client-dns-typo-015` | workload | `workload/client-dependency-hostname` | Client configured with a dependency hostname that does not exist | VALIDATED |
| `wl-client-wrong-port-016` | workload | `workload/client-dependency-port` | Client configured with the wrong port for a dependency | VALIDATED |
| `wl-cpu-throttle-032` | workload | `workload/cpu-limit-throttling` | CPU limit so low the service is throttled into slowness | VALIDATED |
| `wl-crash-invalid-env-013` | workload | `workload/invalid-config-crash` | Invalid configuration value makes the service crash at startup | VALIDATED |
| `wl-dns-policy-none-029` | workload | `workload/pod-dns-config` | Pod DNS set to an unreachable nameserver | VALIDATED |
| `wl-ephemeral-storage-evicted-027` | workload | `workload/ephemeral-storage-eviction` | Tiny ephemeral-storage limit -> pods evicted over and over | VALIDATED |
| `wl-host-alias-poison-028` | workload | `workload/hostaliases-override` | hostAliases entry sends a dependency to a dead IP | VALIDATED |
| `wl-image-pull-011` | workload | `workload/image-pull-failure` | Mistyped image tag -> ImagePullBackOff | VALIDATED |
| `wl-init-container-stuck-026` | workload | `workload/init-container-blocked` | Init container waits for a dependency name that never resolves | VALIDATED |
| `wl-jvm-heap-over-limit-031` | workload | `workload/jvm-heap-exceeds-limit` | Memory limit below the JVM heap the broker is configured to use | VALIDATED |
| `wl-listen-port-drift-014` | workload | `workload/listen-port-drift` | Service listens on a different port than its Kubernetes Service targets | VALIDATED |
| `wl-liveness-wrong-port-023` | workload | `workload/liveness-probe-misconfigured` | Liveness probe checks the wrong port -> restart loop | VALIDATED |
| `wl-missing-configmap-volume-019` | workload | `workload/missing-configmap-volume` | Pod mounts a ConfigMap that does not exist -> stuck ContainerCreating | VALIDATED |
| `wl-missing-secret-020` | workload | `workload/missing-secret-reference` | Env var references a Secret that does not exist -> CreateContainerConfigError | VALIDATED |
| `wl-nodeselector-018` | workload | `workload/unschedulable-node-selector` | nodeSelector matches no node -> Pending | VALIDATED |
| `wl-paused-rollout-trap-030` | workload | `workload/paused-rollout-blocks-fix` | Bad config plus a paused Deployment: the fix does not roll out | VALIDATED |
| `wl-readiness-never-ready-024` | workload | `workload/readiness-probe-misconfigured` | Readiness probe can never succeed -> no endpoints | VALIDATED |
| `wl-readonly-rootfs-022` | workload | `workload/read-only-root-filesystem` | readOnlyRootFilesystem on a server that writes to disk -> crash | VALIDATED |
| `wl-run-as-non-root-021` | workload | `workload/security-context-run-as-non-root` | runAsNonRoot on an image that runs as root -> CreateContainerConfigError | VALIDATED |
| `wl-scaled-to-zero-025` | workload | `workload/scaled-to-zero` | Deployment scaled to zero replicas | VALIDATED |
| `wl-unschedulable-request-017` | workload | `workload/unschedulable-resource-request` | Memory request larger than any node -> Pending | VALIDATED |
