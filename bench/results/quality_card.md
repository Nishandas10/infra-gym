| Scenario | Tier | Layer | Status | Runs | Validated | Flake rate | Detect | Recover | Reset | Last verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| cache-leak-009 | standard | app | validated | 5 | 4 | 20% | 370s | 605s | 10s | VALIDATED |
| catalog-fail-008 | standard | app | validated | 5 | 5 | 0% | 1s | 1s | 9s | VALIDATED |
| compound-quota-blocks-fix-090 | standard | workload | validated | 5 | 5 | 0% | 1s | 1s | 31s | VALIDATED |
| compound-red-herring-092 | standard | workload | validated | 5 | 5 | 0% | 6s | 1s | 9s | VALIDATED |
| compound-two-faults-091 | standard | workload | validated | 5 | 5 | 0% | 4s | 32s | 9s | VALIDATED |
| coredns-down-043 | standard | platform | validated | 5 | 5 | 0% | 42s | 1s | 9s | VALIDATED |
| coredns-rewrite-poison-044 | standard | platform | validated | 5 | 5 | 0% | 46s | 2s | 29s | VALIDATED |
| cpu-stress-004 | standard | workload | draft | 0 | 0 | - | - | - | - | not run |
| dns-error-005 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| dns-random-057 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| flag-ad-failure-064 | standard | app | validated | 5 | 5 | 0% | 2s | 2s | 9s | VALIDATED |
| flag-ad-high-cpu-065 | standard | app | validated | 5 | 5 | 0% | 12s | 33s | 10s | VALIDATED |
| flag-ad-manual-gc-066 | standard | app | validated | 5 | 5 | 0% | 1s | 35s | 14s | VALIDATED |
| flag-cart-failure-067 | standard | app | validated | 5 | 5 | 0% | 46s | 1s | 9s | VALIDATED |
| flag-email-memory-leak-068 | standard | app | validated | 5 | 5 | 0% | 2s | 301s | 9s | VALIDATED |
| flag-flood-homepage-073 | standard | app | validated | 5 | 5 | 0% | 31s | 31s | 10s | VALIDATED |
| flag-image-slow-load-071 | standard | app | validated | 5 | 5 | 0% | 31s | 1s | 9s | VALIDATED |
| flag-intl-shipping-slow-072 | standard | app | validated | 5 | 5 | 0% | 21s | 1s | 9s | VALIDATED |
| grafana-datasource-089 | standard | observability | validated | 5 | 5 | 0% | 23s | 1s | 10s | VALIDATED |
| hard-allowlist-forgets-checkout-106 | hard | service-net | validated | 5 | 5 | 0% | 21s | 12s | 32s | VALIDATED |
| hard-cart-chained-addr-auth-103 | hard | workload | validated | 5 | 5 | 0% | 1s | 23s | 162s | VALIDATED |
| hard-duplicate-env-override-109 | hard | workload | validated | 5 | 5 | 0% | 53s | 33s | 11s | VALIDATED |
| hard-egress-policy-blocks-db-102 | hard | service-net | validated | 5 | 5 | 0% | 49s | 140s | 162s | VALIDATED |
| hard-fix-reverted-by-cronjob-101 | hard | workload | validated | 5 | 5 | 0% | 1s | 153s | 9s | VALIDATED |
| hard-flag-in-source-of-truth-111 | hard | app | validated | 5 | 5 | 0% | 2s | 2s | 32s | VALIDATED |
| hard-ghost-legacy-email-pods-104 | hard | service-net | validated | 5 | 5 | 0% | 11s | 1s | 9s | VALIDATED |
| hard-masked-second-fault-107 | hard | workload | validated | 5 | 5 | 0% | 30s | 2s | 39s | VALIDATED |
| hard-oom-fix-blocked-by-limitrange-110 | hard | workload | validated | 5 | 5 | 0% | 1s | 128s | 11s | VALIDATED |
| hard-pinned-endpoints-108 | hard | service-net | validated | 5 | 5 | 0% | 11s | 17s | 10s | VALIDATED |
| hard-silent-ledger-write-denied-105 | hard | datastore | validated | 5 | 5 | 0% | 96s | 8s | 10s | VALIDATED |
| hard-telemetry-noise-hides-scheduling-112 | hard | node | validated | 5 | 5 | 0% | 25s | 25s | 29s | VALIDATED |
| http-abort-058 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| http-replace-059 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| jvm-exception-062 | standard | app | draft | 0 | 0 | - | - | - | - | not run |
| k8s-oom-cascade-001 | standard | workload | validated | 5 | 5 | 0% | 1s | 123s | 29s | VALIDATED |
| kafka-backlog-010 | standard | app | validated | 5 | 5 | 0% | 5s | 24s | 9s | VALIDATED |
| kafka-broker-down-083 | standard | datastore | validated | 5 | 5 | 0% | 64s | 8s | 47s | VALIDATED |
| kafka-message-too-large-082 | standard | datastore | validated | 5 | 5 | 0% | 65s | 2s | 157s | VALIDATED |
| kube-proxy-stopped-051 | standard | platform | validated | 5 | 5 | 0% | 1s | 45s | 9s | VALIDATED |
| limitrange-rejects-048 | standard | platform | validated | 5 | 5 | 0% | 1s | 23s | 9s | VALIDATED |
| net-bandwidth-053 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| net-delay-002 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| net-packet-loss-052 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| net-partition-054 | standard | network | draft | 0 | 0 | - | - | - | - | not run |
| netpol-default-deny-041 | standard | service-net | validated | 5 | 5 | 0% | 49s | 1s | 10s | VALIDATED |
| netpol-dns-blocked-040 | standard | service-net | validated | 5 | 5 | 0% | 44s | 12s | 9s | VALIDATED |
| netpol-egress-lockdown-039 | standard | service-net | validated | 5 | 5 | 0% | 46s | 2s | 10s | VALIDATED |
| netpol-ingress-deny-038 | standard | service-net | validated | 5 | 5 | 0% | 21s | 11s | 9s | VALIDATED |
| node-cordoned-045 | standard | node | validated | 5 | 5 | 0% | 1s | 24s | 11s | VALIDATED |
| node-taint-046 | standard | node | validated | 5 | 5 | 0% | 25s | 27s | 10s | VALIDATED |
| obs-pii-redaction-removed-069 | standard | observability | validated | 5 | 5 | 0% | 28s | 43s | 30s | VALIDATED |
| otel-collector-unscheduled-086 | standard | observability | validated | 5 | 5 | 0% | 1s | 44s | 11s | VALIDATED |
| otel-exporter-broken-085 | standard | observability | validated | 5 | 5 | 0% | 57s | 23s | 30s | VALIDATED |
| otel-service-endpoint-087 | standard | observability | validated | 5 | 5 | 0% | 53s | 22s | 31s | VALIDATED |
| pay-fail-006 | standard | app | validated | 5 | 4 | 20% | 1s | 1s | 11s | NOT_DETECTED |
| pay-unreachable-007 | standard | app | validated | 5 | 5 | 0% | 1s | 1s | 10s | VALIDATED |
| pg-connection-limit-080 | standard | datastore | validated | 5 | 5 | 0% | 1s | 1s | 11s | VALIDATED |
| pg-lock-held-081 | standard | datastore | validated | 5 | 4 | 20% | 48s | 1s | 9s | VALIDATED |
| pg-password-rotated-079 | standard | datastore | validated | 5 | 5 | 0% | 1s | 1s | 10s | VALIDATED |
| pg-revoked-grant-078 | standard | datastore | validated | 5 | 5 | 0% | 1s | 1s | 9s | VALIDATED |
| pod-failure-055 | standard | workload | draft | 0 | 0 | - | - | - | - | not run |
| pod-kill-003 | standard | workload | draft | 0 | 0 | - | - | - | - | not run |
| pod-security-restricted-049 | standard | platform | validated | 5 | 5 | 0% | 6s | 1s | 10s | VALIDATED |
| prometheus-otlp-disabled-088 | standard | observability | validated | 5 | 5 | 0% | 16s | 11s | 10s | VALIDATED |
| proxy-upstream-misroute-042 | standard | service-net | validated | 5 | 5 | 0% | 42s | 16s | 9s | VALIDATED |
| quota-blocks-pods-047 | standard | platform | validated | 5 | 5 | 0% | 16s | 1s | 9s | VALIDATED |
| svc-deleted-037 | standard | service-net | validated | 5 | 5 | 0% | 1s | 1s | 10s | VALIDATED |
| svc-selector-mismatch-035 | standard | service-net | validated | 5 | 5 | 0% | 1s | 11s | 166s | VALIDATED |
| svc-targetport-mismatch-036 | standard | service-net | validated | 5 | 5 | 0% | 16s | 1s | 42s | VALIDATED |
| valkey-client-pause-077 | standard | datastore | validated | 5 | 5 | 0% | 18s | 1s | 10s | VALIDATED |
| valkey-maxmemory-075 | standard | datastore | validated | 5 | 5 | 0% | 1s | 1s | 10s | VALIDATED |
| valkey-requirepass-076 | standard | datastore | validated | 5 | 5 | 0% | 1s | 23s | 160s | VALIDATED |
| webhook-blocks-pods-050 | standard | platform | validated | 5 | 5 | 0% | 9s | 12s | 10s | VALIDATED |
| wl-bad-command-012 | standard | workload | validated | 5 | 5 | 0% | 6s | 12s | 9s | VALIDATED |
| wl-client-dns-typo-015 | standard | workload | validated | 5 | 5 | 0% | 1s | 14s | 10s | VALIDATED |
| wl-client-wrong-port-016 | standard | workload | validated | 5 | 5 | 0% | 32s | 2s | 30s | VALIDATED |
| wl-cpu-throttle-032 | standard | workload | validated | 5 | 5 | 0% | 11s | 12s | 10s | VALIDATED |
| wl-crash-invalid-env-013 | standard | workload | validated | 5 | 5 | 0% | 16s | 12s | 28s | VALIDATED |
| wl-dns-policy-none-029 | standard | workload | validated | 5 | 5 | 0% | 46s | 18s | 11s | VALIDATED |
| wl-ephemeral-storage-evicted-027 | standard | workload | validated | 5 | 5 | 0% | 11s | 171s | 11s | VALIDATED |
| wl-host-alias-poison-028 | standard | workload | validated | 5 | 5 | 0% | 60s | 17s | 10s | VALIDATED |
| wl-image-pull-011 | standard | workload | validated | 5 | 5 | 0% | 21s | 23s | 10s | VALIDATED |
| wl-init-container-stuck-026 | standard | workload | validated | 5 | 5 | 0% | 1s | 43s | 10s | VALIDATED |
| wl-jvm-heap-over-limit-031 | standard | workload | validated | 5 | 5 | 0% | 65s | 276s | 61s | VALIDATED |
| wl-listen-port-drift-014 | standard | workload | validated | 5 | 5 | 0% | 12s | 12s | 9s | VALIDATED |
| wl-liveness-wrong-port-023 | standard | workload | validated | 5 | 5 | 0% | 1s | 122s | 9s | VALIDATED |
| wl-missing-configmap-volume-019 | standard | workload | validated | 5 | 5 | 0% | 4s | 21s | 10s | VALIDATED |
| wl-missing-secret-020 | standard | workload | validated | 5 | 5 | 0% | 9s | 12s | 11s | VALIDATED |
| wl-nodeselector-018 | standard | workload | validated | 5 | 5 | 0% | 1s | 56s | 11s | VALIDATED |
| wl-paused-rollout-trap-030 | standard | workload | validated | 5 | 5 | 0% | 1s | 12s | 29s | VALIDATED |
| wl-readiness-never-ready-024 | standard | workload | validated | 5 | 5 | 0% | 1s | 22s | 12s | VALIDATED |
| wl-readonly-rootfs-022 | standard | workload | validated | 5 | 5 | 0% | 6s | 1s | 10s | VALIDATED |
| wl-run-as-non-root-021 | standard | workload | validated | 5 | 5 | 0% | 9s | 12s | 11s | VALIDATED |
| wl-scaled-to-zero-025 | standard | workload | validated | 5 | 5 | 0% | 46s | 13s | 11s | VALIDATED |
| wl-unschedulable-request-017 | standard | workload | validated | 5 | 5 | 0% | 1s | 22s | 10s | VALIDATED |

95 scenarios, 415 validation runs, 99% of runs VALIDATED (current versions only)
