"""Catalog of unique scenarios (beyond the 10 hand-written golden ones).

Uniqueness rule: every entry has a distinct `mechanism` key, i.e. a distinct
root-cause class with its own evidence chain and fix. Changing only numbers
(memory size, latency, percentage), names or seeds creates a *variant*, not a
new scenario, and is deliberately not counted here.

scripts/generate_scenarios.py turns each entry into scenarios/<id>/spec.yaml
+ reference_solution.md.
"""
from __future__ import annotations

IMG = "ghcr.io/open-telemetry/demo:3.1.0-{}"
FP = "http://frontend-proxy.default.svc.cluster.local:8080"


# ---------------------------------------------------------------- check helpers
def J(journey, repeat=3, err=0, ms=2500, timeout=None):
    c = {"type": "journey", "journey": journey, "repeat": repeat, "max_error_pct": err, "max_avg_ms": ms}
    if timeout:
        c["timeout_s"] = timeout
    return c


def PODS(name, selector=None, ns=None):
    c = {"type": "pods_ready", "selector": selector or f"opentelemetry.io/name={name}"}
    if ns:
        c["namespace"] = ns
    return c


def STABLE(name, age=90, selector=None):
    return {"type": "pods_stable", "selector": selector or f"opentelemetry.io/name={name}", "min_age_s": age}


def EP(service):
    return {"type": "endpoints", "service": service}


def LAG(group, max_lag=50):
    return {"type": "kafka_lag", "group": group, "max_lag": max_lag}


def TRACES(service, lookback="1m"):
    return {"type": "jaeger_traces", "service": service, "lookback": lookback, "min_traces": 1}


ORDERS = {"type": "orders_recorded", "timeout_s": 60}
COLLECTOR = "app.kubernetes.io/name=opentelemetry-collector"


def rollout(name, ns=""):
    n = f" -n {ns}" if ns else ""
    return f"kubectl{n} rollout status deployment/{name} --timeout=300s"


def env_op(var, value):
    return {"op": "replace", "path": f"/spec/template/spec/containers/$c/env/$name:{var}/value", "value": value}


KAFKA_TOPIC_FIX = ("for i in $(seq 1 24); do kubectl exec -n gym-system deploy/gym-kafka-tools -- "
                   "/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka.default.svc.cluster.local:9092 "
                   "--create --if-not-exists --topic orders --partitions 1 --replication-factor 1 && break; "
                   "sleep 5; done")


def jpatch(kind, name, ops_json, ns=""):
    n = f" -n {ns}" if ns else ""
    return f"kubectl{n} patch {kind} {name} --type=json -p '{ops_json}'"


def S(id, family, mechanism, title, fault, prompt, checks, solution, cause, diagnose, root=None,
      detect=240, recover=300, hold=30, poll=10, baseline=120, notes=None):
    return {"id": id, "family": family, "mechanism": mechanism, "title": title, "fault": fault,
            "prompt": prompt, "checks": checks, "solution": solution, "cause": cause, "diagnose": diagnose,
            "root": root or [], "validation": {"detect_timeout_s": detect, "recover_timeout_s": recover,
                                               "hold_s": hold, "poll_s": poll, "baseline_timeout_s": baseline},
            "notes": notes}


CATALOG = [
    # =================================================================== workload spec
    S("wl-image-pull-011", "workload", "workload/image-pull-failure",
      "Mistyped image tag -> ImagePullBackOff",
      {"type": "workload_patch", "target": "currency", "strategy": "Recreate",
       "ops": [{"op": "replace", "path": "/spec/template/spec/containers/$c/image", "value": IMG.format("curency")}]},
      "Prices no longer show when customers switch currency, and every order fails. Find the cause and fix it.",
      [J("currency"), J("checkout"), PODS("currency")],
      [f"kubectl set image deployment/currency currency={IMG.format('currency')}", rollout("currency")],
      "The currency Deployment's image tag was mistyped (`3.1.0-curency`). The registry has no such image, "
      "so the new pod is stuck in ImagePullBackOff, and the Recreate strategy removed the old pod first.",
      ["`kubectl get pods`: currency is `ErrImagePull` / `ImagePullBackOff`.",
       "`kubectl describe pod -l opentelemetry.io/name=currency`: events say the image tag was not found.",
       "`kubectl get deploy currency -o jsonpath='{.spec.template.spec.containers[0].image}'` shows the typo."],
      root=["currency"]),

    S("wl-bad-command-012", "workload", "workload/bad-entrypoint",
      "Container command points at a binary that does not exist",
      {"type": "workload_patch", "target": "quote", "strategy": "Recreate",
       "ops": [{"op": "set", "path": "/spec/template/spec/containers/$c/command",
                "value": ["/usr/local/bin/quote-server"]}]},
      "Every order fails with a shipping error. The shipping service itself is Running. Find the cause and fix it.",
      [J("checkout"), PODS("quote")],
      [jpatch("deployment", "quote", '[{"op":"remove","path":"/spec/template/spec/containers/0/command"}]'),
       rollout("quote")],
      "The quote Deployment overrides the container command with `/usr/local/bin/quote-server`, which does "
      "not exist in the image. The container can never start, so shipping cannot get a price quote and "
      "checkout fails two hops away from the real problem.",
      ["`kubectl logs deploy/checkout`: the shipping quote call fails.",
       "`kubectl logs deploy/shipping`: requests to quote fail.",
       "`kubectl get pods`: quote is `RunContainerError` / `CrashLoopBackOff`; `kubectl describe` says "
       "`exec: \"/usr/local/bin/quote-server\": no such file or directory`.",
       "The Deployment spec has a `command:` override the image does not support."],
      root=["quote"]),

    S("wl-crash-invalid-env-013", "workload", "workload/invalid-config-crash",
      "Invalid configuration value makes the service crash at startup",
      {"type": "workload_patch", "target": "shipping", "strategy": "Recreate",
       "ops": [env_op("SHIPPING_PORT", "eighty-eighty")]},
      "Since the last configuration change every order fails at the shipping step. Find the cause and fix it.",
      [J("checkout"), PODS("shipping")],
      ["kubectl set env deployment/shipping SHIPPING_PORT=8080", rollout("shipping")],
      "`SHIPPING_PORT` was set to `eighty-eighty`. The shipping service cannot parse it into a listen "
      "address and exits at startup, so it crash-loops.",
      ["`kubectl get pods`: shipping is in `CrashLoopBackOff`.",
       "`kubectl logs deploy/shipping --previous`: startup error about the port / bind address.",
       "`kubectl get deploy shipping -o yaml`: `SHIPPING_PORT` has an invalid value."],
      root=["shipping"]),

    S("wl-listen-port-drift-014", "workload", "workload/listen-port-drift",
      "Service listens on a different port than its Kubernetes Service targets",
      {"type": "workload_patch", "target": "payment", "recreate_pods": False,
       "ops": [env_op("PAYMENT_PORT", "8081")]},
      "Every order fails at the payment step. The payment pod is Running with zero restarts and its logs "
      "look normal. Find the cause and fix it.",
      [J("checkout")],
      ["kubectl set env deployment/payment PAYMENT_PORT=8080", rollout("payment")],
      "`PAYMENT_PORT` was changed to 8081, so the payment server now listens on 8081 while the `payment` "
      "Service still sends traffic to targetPort 8080. The pod looks perfectly healthy because it has no "
      "probes, and every connection to it is refused.",
      ["`kubectl logs deploy/checkout`: `connection refused` when calling payment.",
       "`kubectl logs deploy/payment`: the server says it is listening on port 8081.",
       "`kubectl get svc payment -o yaml`: targetPort is 8080, a mismatch."],
      root=["payment"]),

    S("wl-client-dns-typo-015", "workload", "workload/client-dependency-hostname",
      "Client configured with a dependency hostname that does not exist",
      {"type": "workload_patch", "target": "frontend", "recreate_pods": False,
       "ops": [env_op("CART_ADDR", "cart-service:8080")]},
      "Customers cannot add anything to their cart; the cart shows an error. Browsing products works. "
      "Find the cause and fix it.",
      [J("cart"), J("checkout")],
      ["kubectl set env deployment/frontend CART_ADDR=cart:8080", rollout("frontend")],
      "The frontend's `CART_ADDR` points at `cart-service:8080`. No Service has that name, so every cart "
      "call from the frontend fails DNS resolution. The cart service itself is fine.",
      ["`kubectl get pods`: everything is Running.",
       "`kubectl logs deploy/frontend`: errors resolving `cart-service` (ENOTFOUND / name resolution).",
       "`kubectl get svc`: there is no `cart-service`, only `cart`.",
       "`kubectl get deploy frontend -o yaml`: `CART_ADDR=cart-service:8080`."],
      root=["frontend"]),

    S("wl-client-wrong-port-016", "workload", "workload/client-dependency-port",
      "Client configured with the wrong port for a dependency",
      {"type": "workload_patch", "target": "checkout", "recreate_pods": False,
       "ops": [env_op("PRODUCT_CATALOG_ADDR", "product-catalog:9090")]},
      "Browsing and the cart work, but placing an order always fails. Find the cause and fix it.",
      [J("checkout")],
      ["kubectl set env deployment/checkout PRODUCT_CATALOG_ADDR=product-catalog:8080", rollout("checkout")],
      "Checkout's `PRODUCT_CATALOG_ADDR` uses port 9090. The product-catalog Service only exposes 8080, so "
      "checkout cannot look up product prices. Browsing still works because the frontend uses the right "
      "address.",
      ["`kubectl logs deploy/checkout`: `connection refused` / unavailable for product-catalog.",
       "The frontend can reach product-catalog, so the catalog itself is healthy.",
       "`kubectl get deploy checkout -o yaml` vs `kubectl get svc product-catalog`: port mismatch 9090 vs 8080."],
      root=["checkout"]),

    S("wl-unschedulable-request-017", "workload", "workload/unschedulable-resource-request",
      "Memory request larger than any node -> Pending",
      {"type": "workload_patch", "target": "recommendation", "strategy": "Recreate",
       "ops": [{"op": "replace", "path": "/spec/template/spec/containers/$c/resources",
                "value": {"limits": {"memory": "64Gi"}, "requests": {"memory": "64Gi"}}}]},
      "The 'You may also like' panel is empty on every product page since this morning's resource tuning. "
      "Find the cause and fix it.",
      [J("recommendations"), PODS("recommendation")],
      ["kubectl set resources deployment/recommendation -c recommendation --limits=memory=500Mi "
       "--requests=memory=500Mi", rollout("recommendation")],
      "The recommendation container now requests 64Gi of memory. No node has that much allocatable memory, "
      "so the pod stays Pending forever.",
      ["`kubectl get pods`: recommendation is `Pending`.",
       "`kubectl describe pod -l opentelemetry.io/name=recommendation`: `FailedScheduling ... Insufficient memory`.",
       "`kubectl get deploy recommendation -o yaml`: requests/limits of 64Gi."],
      root=["recommendation"]),

    S("wl-nodeselector-018", "workload", "workload/unschedulable-node-selector",
      "nodeSelector matches no node -> Pending",
      {"type": "workload_patch", "target": "ad", "strategy": "Recreate",
       "ops": [{"op": "set", "path": "/spec/template/spec/nodeSelector", "value": {"disktype": "ssd"}}]},
      "The advertisement banner has disappeared from the shop. Find the cause and fix it.",
      [J("ads"), PODS("ad")],
      [jpatch("deployment", "ad", '[{"op":"remove","path":"/spec/template/spec/nodeSelector"}]'), rollout("ad")],
      "The ad Deployment was given `nodeSelector: disktype=ssd`. No node carries that label, so the "
      "scheduler cannot place the pod.",
      ["`kubectl get pods`: ad is `Pending`.",
       "`kubectl describe pod -l opentelemetry.io/name=ad`: `didn't match Pod's node affinity/selector`.",
       "`kubectl get nodes --show-labels`: no node has `disktype=ssd`."],
      root=["ad"]),

    S("wl-missing-configmap-volume-019", "workload", "workload/missing-configmap-volume",
      "Pod mounts a ConfigMap that does not exist -> stuck ContainerCreating",
      {"type": "workload_patch", "target": "fraud-detection", "strategy": "Recreate",
       "ops": [{"op": "append", "path": "/spec/template/spec/volumes",
                "value": {"name": "rules", "configMap": {"name": "fraud-rules"}}},
               {"op": "append", "path": "/spec/template/spec/containers/$c/volumeMounts",
                "value": {"name": "rules", "mountPath": "/etc/fraud-rules"}}]},
      "The fraud team says no new orders have reached their system for a while, although checkout works. "
      "Find the cause and fix it.",
      [PODS("fraud-detection"), LAG("fraud-detection")],
      ["kubectl rollout undo deployment/fraud-detection", rollout("fraud-detection")],
      "The last change to fraud-detection mounts a ConfigMap named `fraud-rules` that was never created. "
      "The kubelet cannot set up the volume, so the pod never starts and the Kafka consumer group has no "
      "members. Orders pile up unread. Checkout is unaffected, so the failure is silent.",
      ["`kubectl get pods`: fraud-detection is stuck in `ContainerCreating`.",
       "`kubectl describe pod -l opentelemetry.io/name=fraud-detection`: `FailedMount ... configmap \"fraud-rules\" not found`.",
       "Kafka: consumer group `fraud-detection` has no active members and growing lag.",
       "`kubectl rollout history deployment/fraud-detection`: the latest revision added the volume."],
      root=["fraud-detection"]),

    S("wl-missing-secret-020", "workload", "workload/missing-secret-reference",
      "Env var references a Secret that does not exist -> CreateContainerConfigError",
      {"type": "workload_patch", "target": "email", "strategy": "Recreate",
       "ops": [{"op": "append", "path": "/spec/template/spec/containers/$c/env",
                "value": {"name": "SMTP_PASSWORD",
                          "valueFrom": {"secretKeyRef": {"name": "email-smtp-credentials", "key": "password"}}}}]},
      "Customers report they no longer receive order confirmation emails. Orders themselves succeed. "
      "Find the cause and fix it.",
      [J("email"), PODS("email")],
      ["kubectl set env deployment/email SMTP_PASSWORD-", rollout("email")],
      "The email Deployment now reads `SMTP_PASSWORD` from Secret `email-smtp-credentials`, which does not "
      "exist, so the container cannot be created. Checkout only logs email failures, so orders still "
      "succeed and nobody notices.",
      ["`kubectl get pods`: email is `CreateContainerConfigError`.",
       "`kubectl describe pod -l opentelemetry.io/name=email`: `secret \"email-smtp-credentials\" not found`.",
       "`kubectl logs deploy/checkout`: warnings that the order confirmation could not be sent."],
      root=["email"]),

    S("wl-run-as-non-root-021", "workload", "workload/security-context-run-as-non-root",
      "runAsNonRoot on an image that runs as root -> CreateContainerConfigError",
      {"type": "workload_patch", "target": "astronomy-db", "strategy": "Recreate",
       "ops": [{"op": "set", "path": "/spec/template/spec/securityContext/runAsNonRoot", "value": True}]},
      "Product pages and the catalog fail to load after a security hardening change. Find the cause and fix it.",
      [J("browse"), J("catalog"), PODS("astronomy-db")],
      [jpatch("deployment", "astronomy-db",
              '[{"op":"remove","path":"/spec/template/spec/securityContext/runAsNonRoot"}]'),
       rollout("astronomy-db")],
      "Hardening added `runAsNonRoot: true` to the Postgres pod. The postgres image starts as root (its "
      "entrypoint drops privileges itself), so the kubelet refuses to start it. With the database gone, "
      "product-catalog cannot serve products.",
      ["`kubectl logs deploy/product-catalog`: database connection errors.",
       "`kubectl get pods`: astronomy-db is `CreateContainerConfigError`.",
       "`kubectl describe pod -l opentelemetry.io/name=astronomy-db`: `container has runAsNonRoot and image will run as root`."],
      root=["astronomy-db"]),

    S("wl-readonly-rootfs-022", "workload", "workload/read-only-root-filesystem",
      "readOnlyRootFilesystem on a server that writes to disk -> crash",
      {"type": "workload_patch", "target": "image-provider", "strategy": "Recreate",
       "ops": [{"op": "set", "path": "/spec/template/spec/containers/$c/securityContext/readOnlyRootFilesystem",
                "value": True}]},
      "All product images in the shop are broken, although the pages themselves load. Find the cause and fix it.",
      [J("images"), PODS("image-provider")],
      [jpatch("deployment", "image-provider",
              '[{"op":"remove","path":"/spec/template/spec/containers/0/securityContext/readOnlyRootFilesystem"}]'),
       rollout("image-provider")],
      "image-provider (nginx) was given a read-only root filesystem, but nginx must write its pid file and "
      "cache under `/run` and `/var/cache/nginx`. It exits at startup.",
      ["`kubectl get pods`: image-provider is in `CrashLoopBackOff`.",
       "`kubectl logs deploy/image-provider --previous`: `Read-only file system` errors.",
       "`kubectl get deploy image-provider -o yaml`: `readOnlyRootFilesystem: true`."],
      root=["image-provider"]),

    S("wl-liveness-wrong-port-023", "workload", "workload/liveness-probe-misconfigured",
      "Liveness probe checks the wrong port -> restart loop",
      {"type": "workload_patch", "target": "product-catalog", "recreate_pods": False,
       "ops": [{"op": "set", "path": "/spec/template/spec/containers/$c/livenessProbe",
                "value": {"tcpSocket": {"port": 9999}, "initialDelaySeconds": 5, "periodSeconds": 5,
                          "failureThreshold": 2}}]},
      "Product pages fail every few seconds, and the product-catalog pod's restart count keeps rising. "
      "Find the cause and fix it.",
      [STABLE("product-catalog", 120), J("browse", repeat=4), J("catalog")],
      [jpatch("deployment", "product-catalog",
              '[{"op":"remove","path":"/spec/template/spec/containers/0/livenessProbe"}]'),
       rollout("product-catalog")],
      "A liveness probe was added that checks TCP port 9999; the service listens on 8080. The kubelet kills "
      "the healthy container every ~15 seconds.",
      ["`kubectl get pods -w`: product-catalog restarts repeatedly.",
       "`kubectl describe pod -l opentelemetry.io/name=product-catalog`: `Liveness probe failed: dial tcp ...:9999: connection refused`.",
       "The app logs show normal startup each time, so it isn't crashing by itself."],
      recover=360, root=["product-catalog"]),

    S("wl-readiness-never-ready-024", "workload", "workload/readiness-probe-misconfigured",
      "Readiness probe can never succeed -> no endpoints",
      {"type": "workload_patch", "target": "cart", "strategy": "Recreate",
       "ops": [{"op": "set", "path": "/spec/template/spec/containers/$c/readinessProbe",
                "value": {"httpGet": {"path": "/healthz", "port": 8080}, "periodSeconds": 5}}]},
      "The cart is broken for everyone: adding items fails and orders fail. The cart pod is Running. "
      "Find the cause and fix it.",
      [J("cart"), EP("cart")],
      [jpatch("deployment", "cart", '[{"op":"remove","path":"/spec/template/spec/containers/0/readinessProbe"}]'),
       rollout("cart")],
      "A readiness probe was added that does an HTTP GET on `/healthz`. The cart server only speaks gRPC "
      "and has no such endpoint, so the pod is never Ready and the `cart` Service has no endpoints.",
      ["`kubectl get pods`: cart is Running but `0/1` READY.",
       "`kubectl describe pod -l opentelemetry.io/name=cart`: `Readiness probe failed`.",
       "`kubectl get endpointslices -l kubernetes.io/service-name=cart`: no ready endpoints."],
      root=["cart"]),

    S("wl-scaled-to-zero-025", "workload", "workload/scaled-to-zero",
      "Deployment scaled to zero replicas",
      {"type": "workload_patch", "target": "checkout", "recreate_pods": False,
       "ops": [{"op": "replace", "path": "/spec/replicas", "value": 0}]},
      "Browsing and the cart work, but 'Place Order' always fails. Find the cause and fix it.",
      [J("checkout"), EP("checkout")],
      ["kubectl scale deployment checkout --replicas=1", rollout("checkout")],
      "The checkout Deployment was scaled to 0 replicas (a leftover of a maintenance action), so there is "
      "no checkout pod at all.",
      ["`kubectl get pods`: no checkout pod.",
       "`kubectl get deploy checkout`: `0/0` replicas.",
       "`kubectl logs deploy/frontend`: checkout calls fail (unavailable / no endpoints)."],
      root=["checkout"]),

    S("wl-init-container-stuck-026", "workload", "workload/init-container-blocked",
      "Init container waits for a dependency name that never resolves",
      {"type": "workload_patch", "target": "cart", "strategy": "Recreate",
       "ops": [{"op": "replace", "path": "/spec/template/spec/initContainers/$name:wait-for-valkey-cart/command",
                "value": ["sh", "-c", "until nc -z -v -w30 valkey-cart-primary 6379; do "
                                      "echo waiting for valkey-cart; sleep 2; done;"]}]},
      "The cart has been down since the last deploy. The new cart pod never becomes Ready. "
      "Find the cause and fix it.",
      [J("cart"), PODS("cart")],
      ["kubectl rollout undo deployment/cart", rollout("cart")],
      "The init container `wait-for-valkey-cart` was changed to wait for `valkey-cart-primary`, a host "
      "that does not exist. The init container loops forever and the main container never starts.",
      ["`kubectl get pods`: cart is `Init:0/1`.",
       "`kubectl logs <cart-pod> -c wait-for-valkey-cart`: repeated `waiting for valkey-cart` / name resolution errors.",
       "`kubectl get deploy cart -o yaml`: the init command uses `valkey-cart-primary`.",
       "`kubectl rollout history deployment/cart` shows the change; rolling back fixes it."],
      root=["cart"]),

    S("wl-ephemeral-storage-evicted-027", "workload", "workload/ephemeral-storage-eviction",
      "Tiny ephemeral-storage limit -> pods evicted over and over",
      {"type": "workload_patch", "kind": "daemonset", "target": "otel-collector-agent", "recreate_pods": False,
       "revert_hooks": [{"delete_failed_pods": True}],
       "ops": [{"op": "set",
                "path": "/spec/template/spec/containers/$c/resources/limits/ephemeral-storage", "value": "64Ki"}]},
      "Traces keep disappearing from Jaeger for minutes at a time, and the telemetry collector pods keep "
      "being replaced. Find the cause and fix it.",
      [STABLE("collector", 180, selector=COLLECTOR), TRACES("frontend")],
      [jpatch("daemonset", "otel-collector-agent",
              '[{"op":"remove","path":"/spec/template/spec/containers/0/resources/limits/ephemeral-storage"}]'),
       "kubectl rollout status daemonset/otel-collector-agent --timeout=240s",
       "kubectl delete pods --field-selector=status.phase=Failed"],
      "The collector DaemonSet got an `ephemeral-storage` limit of 64Ki. Container logs count toward that "
      "limit, and the collector's debug exporter logs continuously, so the kubelet evicts the pods soon "
      "after they start.",
      ["`kubectl get pods -l app.kubernetes.io/name=opentelemetry-collector`: pods `Evicted` / constantly new.",
       "`kubectl describe pod <evicted-pod>`: `Pod ephemeral local storage usage exceeds the total limit of containers 64Ki`.",
       "`kubectl get ds otel-collector-agent -o yaml`: the ephemeral-storage limit."],
      detect=300, recover=420, root=["otel-collector"]),

    S("wl-host-alias-poison-028", "workload", "workload/hostaliases-override",
      "hostAliases entry sends a dependency to a dead IP",
      {"type": "workload_patch", "target": "frontend", "recreate_pods": False,
       "ops": [{"op": "set", "path": "/spec/template/spec/hostAliases",
                "value": [{"ip": "192.0.2.10", "hostnames": ["product-catalog"]}]}]},
      "Product listings and product pages time out, but checkout (which also uses the catalog) works. "
      "Find the cause and fix it.",
      [J("browse"), J("catalog")],
      [jpatch("deployment", "frontend", '[{"op":"remove","path":"/spec/template/spec/hostAliases"}]'),
       rollout("frontend")],
      "The frontend pod template has a `hostAliases` entry mapping `product-catalog` to 192.0.2.10 (an "
      "unroutable test address), which overrides DNS inside the pod through /etc/hosts. Only the frontend "
      "is affected, which is why checkout still works.",
      ["`kubectl logs deploy/frontend`: timeouts calling product-catalog.",
       "Product-catalog is healthy and reachable from other pods (checkout works).",
       "`kubectl exec deploy/frontend -- cat /etc/hosts`: `192.0.2.10 product-catalog`.",
       "`kubectl get deploy frontend -o yaml`: `hostAliases`."],
      root=["frontend"]),

    S("wl-dns-policy-none-029", "workload", "workload/pod-dns-config",
      "Pod DNS set to an unreachable nameserver",
      # Recreate: checkout's init container also needs DNS, so a rolling update would
      # leave the old pod serving and never cause an outage.
      {"type": "workload_patch", "target": "checkout", "strategy": "Recreate",
       "ops": [{"op": "set", "path": "/spec/template/spec/dnsPolicy", "value": "None"},
               {"op": "set", "path": "/spec/template/spec/dnsConfig",
                "value": {"nameservers": ["192.0.2.53"], "searches": ["default.svc.cluster.local"]}}]},
      "Placing an order fails with errors about every dependency at once. Other services work. "
      "Find the cause and fix it.",
      [J("checkout")],
      [jpatch("deployment", "checkout", '[{"op":"replace","path":"/spec/template/spec/dnsPolicy","value":'
                                        '"ClusterFirst"},{"op":"remove","path":"/spec/template/spec/dnsConfig"}]'),
       rollout("checkout")],
      "The checkout pod template sets `dnsPolicy: None` with a nameserver at 192.0.2.53 that does not "
      "exist, so checkout cannot resolve any service name. Every dependency fails at once.",
      ["`kubectl logs deploy/checkout`: every outgoing call fails with name-resolution errors.",
       "Other pods resolve names fine, so it is not a cluster-wide DNS outage.",
       "`kubectl exec deploy/checkout -- cat /etc/resolv.conf` (or the pod spec): nameserver 192.0.2.53, "
       "`dnsPolicy: None`."],
      root=["checkout"]),

    S("wl-paused-rollout-trap-030", "workload", "workload/paused-rollout-blocks-fix",
      "Bad config plus a paused Deployment: the fix does not roll out",
      {"type": "composite", "steps": [
          {"type": "workload_patch", "target": "cart", "recreate_pods": False,
           "ops": [env_op("VALKEY_ADDR", "valkey-cart-v2:6379")], "pause_s": 25},
          {"type": "workload_patch", "target": "cart", "recreate_pods": False,
           "ops": [{"op": "set", "path": "/spec/paused", "value": True}]}]},
      "The cart is broken: adding items fails. A colleague says they already fixed the config, but nothing "
      "changed. Find the cause and fix it for real.",
      [J("cart")],
      ["kubectl set env deployment/cart VALKEY_ADDR=valkey-cart:6379", "kubectl rollout resume deployment/cart",
       rollout("cart")],
      "Cart's `VALKEY_ADDR` was pointed at `valkey-cart-v2`, which does not exist. The Deployment was then "
      "paused, so any corrected template, including the colleague's fix, is recorded but never rolled out.",
      ["`kubectl logs deploy/cart`: cannot connect to `valkey-cart-v2`.",
       "`kubectl get deploy cart -o yaml`: `paused: true`; `kubectl rollout status` says the rollout is paused.",
       "After fixing the env var, `kubectl rollout resume deployment/cart` is needed for it to take effect."],
      root=["cart"]),

    S("wl-jvm-heap-over-limit-031", "workload", "workload/jvm-heap-exceeds-limit",
      "Memory limit below the JVM heap the broker is configured to use",
      # Measured: at 300Mi the JVM runs for minutes (heap pages are only touched as used),
      # at 200Mi it OOMs twice then settles, at 150Mi it crash-loops with OOMKilled.
      {"type": "workload_patch", "target": "kafka", "strategy": "Recreate",
       "restart_on_revert": ["deployment/checkout", "deployment/accounting", "deployment/fraud-detection"],
       "revert_hooks": [{"kafka_topic": "orders"}],
       "ops": [{"op": "replace", "path": "/spec/template/spec/containers/$c/resources/limits/memory",
                "value": "128Mi"}]},
      "Finance says no new orders are being recorded, the fraud team sees nothing new, and placing orders "
      "has become unreliable. Find the cause and fix it.",
      [PODS("kafka"), STABLE("kafka", 300), ORDERS],
      ["kubectl set resources deployment/kafka -c kafka --limits=memory=700Mi", rollout("kafka"),
       KAFKA_TOPIC_FIX,
       "kubectl rollout restart deployment/checkout deployment/accounting deployment/fraud-detection",
       rollout("checkout"), rollout("accounting"), rollout("fraud-detection")],
      "The Kafka broker's memory limit was cut to 128Mi, but it runs with `KAFKA_HEAP_OPTS=-Xmx400M -Xms400M`. "
      "The JVM needs far more than the limit, so the broker is OOMKilled on every start and crash-loops. "
      "Accounting and fraud-detection receive nothing. Checkout's Kafka producer also gets stuck when the "
      "broker disappears, so orders start timing out, and it has to be restarted after the broker is fixed.",
      ["`kubectl get pods`: kafka `CrashLoopBackOff`; `kubectl describe pod` shows `OOMKilled`, exit code 137.",
       "`kubectl get deploy kafka -o yaml`: limit 128Mi vs `KAFKA_HEAP_OPTS=-Xmx400M -Xms400M`.",
       "accounting/fraud-detection logs: broker unavailable; checkout requests time out.",
       "After raising the limit, recreate the `orders` topic if the broker lost it (this demo Kafka has no "
       "persistent volume) and restart checkout and the consumers."],
      detect=300, recover=600, root=["kafka"]),

    S("wl-cpu-throttle-032", "workload", "workload/cpu-limit-throttling",
      "CPU limit so low the service is throttled into slowness",
      {"type": "workload_patch", "target": "frontend", "recreate_pods": False,
       "ops": [{"op": "set", "path": "/spec/template/spec/containers/$c/resources/limits/cpu", "value": "20m"}]},
      "The whole shop has become very slow since yesterday's resource tuning, but nothing is failing and no "
      "pod is restarting. Find the cause and fix it.",
      [J("home", ms=1500), J("browse", ms=1500)],
      [jpatch("deployment", "frontend",
              '[{"op":"remove","path":"/spec/template/spec/containers/0/resources/limits/cpu"}]'),
       rollout("frontend")],
      "The frontend got a CPU limit of 20m (2% of a core). The CFS scheduler throttles it for most of every "
      "100ms period, so each page takes seconds even though nothing errors.",
      ["Latency is high on every page, errors are low, and there are no restarts.",
       "`kubectl get deploy frontend -o yaml`: `limits.cpu: 20m`.",
       "Container CPU usage is pinned at the limit (Grafana, or kubelet stats); throttling metrics climb."],
      root=["frontend"]),

    # =========================================================== services & network
    S("svc-selector-mismatch-035", "service-network", "service/selector-mismatch",
      "Service selector matches no pods -> no endpoints",
      {"type": "object_patch", "kind": "service", "name": "product-catalog",
       "restart_after": ["deployment/product-catalog"],
       "ops": [{"op": "replace", "path": "/spec/selector",
                "value": {"opentelemetry.io/name": "product-catalog-v2"}}]},
      "Product pages, recommendations and checkout all fail. The product-catalog pod is Running and Ready. "
      "Find the cause and fix it.",
      [J("browse"), EP("product-catalog")],
      [jpatch("service", "product-catalog",
              '[{"op":"replace","path":"/spec/selector","value":{"opentelemetry.io/name":"product-catalog"}}]')],
      "The `product-catalog` Service selector was changed to `opentelemetry.io/name=product-catalog-v2`, "
      "which no pod carries, so the Service has no endpoints.",
      ["`kubectl get endpointslices -l kubernetes.io/service-name=product-catalog`: no endpoints.",
       "`kubectl get svc product-catalog -o yaml`: selector `product-catalog-v2`.",
       "`kubectl get pods --show-labels`: the pod is labelled `product-catalog`."],
      root=["product-catalog"]),

    S("svc-targetport-mismatch-036", "service-network", "service/target-port-mismatch",
      "Service targetPort points at a port nothing listens on",
      {"type": "object_patch", "kind": "service", "name": "shipping", "restart_after": ["deployment/shipping"],
       "ops": [{"op": "replace", "path": "/spec/ports/0/targetPort", "value": 8888}]},
      "Orders fail at the shipping step. Shipping's pod is healthy and its logs show no errors. "
      "Find the cause and fix it.",
      [J("checkout")],
      [jpatch("service", "shipping", '[{"op":"replace","path":"/spec/ports/0/targetPort","value":8080}]')],
      "The `shipping` Service's targetPort was changed to 8888. The pod listens on 8080, so connections "
      "through the Service are refused while the pod looks perfectly healthy.",
      ["`kubectl logs deploy/checkout`: connection refused calling shipping.",
       "`kubectl get svc shipping -o yaml`: `targetPort: 8888`.",
       "`kubectl get endpointslices -l kubernetes.io/service-name=shipping -o yaml`: port 8888."],
      root=["shipping"]),

    S("svc-deleted-037", "service-network", "service/deleted",
      "Service object deleted",
      {"type": "delete_object", "kind": "service", "name": "email"},
      "Customers stopped receiving order confirmation emails today. Orders go through. Find the cause and fix it.",
      [J("email")],
      ["bash scripts/reset_world.sh"],
      "The `email` Service was deleted, so the name `email` no longer resolves. Checkout only logs the "
      "failed send, so orders keep succeeding. Helm still has the Service in its release, so re-syncing "
      "the release recreates it.",
      ["`kubectl logs deploy/checkout`: `lookup email ... no such host` when sending confirmations.",
       "`kubectl get svc email`: NotFound, while the email pod is Running.",
       "Recreate it from the source of truth (`helm upgrade` via `scripts/reset_world.sh`), not by hand, "
       "so Helm keeps ownership."],
      recover=480, root=["email"]),

    S("netpol-ingress-deny-038", "service-network", "network-policy/ingress-deny",
      "NetworkPolicy blocks all traffic into a service",
      {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=payment"],
       "manifests": [{"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                      "metadata": {"name": "payment-ingress-lockdown", "namespace": "default"},
                      "spec": {"podSelector": {"matchLabels": {"opentelemetry.io/name": "payment"}},
                               "policyTypes": ["Ingress"]}}]},
      "Every order fails at payment with a timeout. The payment pod is healthy. Find the cause and fix it.",
      [J("checkout")],
      ["kubectl delete networkpolicy payment-ingress-lockdown"],
      "A NetworkPolicy `payment-ingress-lockdown` selects the payment pods and allows no ingress, so "
      "checkout's connections to payment are silently dropped (timeouts, not refusals).",
      ["`kubectl logs deploy/checkout`: payment calls time out.",
       "`kubectl get networkpolicy`: `payment-ingress-lockdown` selects the payment pods with no ingress rules.",
       "Deleting (or fixing) the policy restores traffic."],
      root=["payment"]),

    S("netpol-egress-lockdown-039", "service-network", "network-policy/egress-deny",
      "Egress policy lets a service reach nothing but DNS",
      {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=checkout"],
       "manifests": [{"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                      "metadata": {"name": "checkout-egress-lockdown", "namespace": "default"},
                      "spec": {"podSelector": {"matchLabels": {"opentelemetry.io/name": "checkout"}},
                               "policyTypes": ["Egress"],
                               "egress": [{"to": [{"namespaceSelector": {"matchLabels": {
                                   "kubernetes.io/metadata.name": "kube-system"}}}],
                                   "ports": [{"protocol": "UDP", "port": 53}, {"protocol": "TCP", "port": 53}]}]}}]},
      "Checkout has been down since a security policy rollout; its new pod never becomes Ready. "
      "Find the cause and fix it.",
      [J("checkout"), PODS("checkout")],
      ["kubectl delete networkpolicy checkout-egress-lockdown", "kubectl rollout restart deployment/checkout",
       rollout("checkout")],
      "An egress NetworkPolicy lets checkout pods reach only DNS. Checkout's init container waits for Kafka "
      "and can never connect, so the pod stays in `Init:0/1`. Even if it started, every dependency call "
      "would be blocked.",
      ["`kubectl get pods`: checkout is `Init:0/1`.",
       "`kubectl logs <checkout-pod> -c wait-for-kafka`: `waiting for kafka` forever (the name resolves; "
       "the connection fails).",
       "`kubectl get networkpolicy checkout-egress-lockdown -o yaml`: egress allowed only to port 53."],
      root=["checkout"]),

    S("netpol-dns-blocked-040", "service-network", "network-policy/dns-egress-blocked",
      "Egress policy allows app ports but blocks DNS",
      {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=frontend"],
       "manifests": [{"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                      "metadata": {"name": "frontend-egress-app-ports", "namespace": "default"},
                      "spec": {"podSelector": {"matchLabels": {"opentelemetry.io/name": "frontend"}},
                               "policyTypes": ["Egress"],
                               "egress": [{"ports": [{"protocol": "TCP", "port": 8080}]}]}}]},
      "Every API call from the shop fails after a network-policy change, even though all backends are "
      "healthy and port 8080 is explicitly allowed. Find the cause and fix it.",
      [J("browse"), J("cart")],
      ["kubectl delete networkpolicy frontend-egress-app-ports", "kubectl rollout restart deployment/frontend",
       rollout("frontend")],
      "The egress policy on the frontend allows TCP 8080 to anywhere but nothing else, so DNS (UDP/TCP 53) "
      "is blocked. The frontend cannot resolve any service name, so the allowed port never gets used.",
      ["`kubectl logs deploy/frontend`: name resolution errors (EAI_AGAIN / getaddrinfo).",
       "`kubectl get networkpolicy frontend-egress-app-ports -o yaml`: only TCP 8080 is allowed; no rule for port 53.",
       "Add a DNS rule or remove the policy."],
      root=["frontend"]),

    S("netpol-default-deny-041", "service-network", "network-policy/namespace-default-deny",
      "Namespace-wide default-deny ingress policy",
      {"type": "create_objects",
       "manifests": [{"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                      "metadata": {"name": "default-deny-ingress", "namespace": "default"},
                      "spec": {"podSelector": {}, "policyTypes": ["Ingress"]}}]},
      "The entire shop is unreachable and internal calls time out, right after the security team applied "
      "'baseline' policies. Find the cause and fix it.",
      [J("home"), J("browse")],
      ["kubectl delete networkpolicy default-deny-ingress"],
      "A `default-deny-ingress` NetworkPolicy with an empty podSelector blocks all new inbound connections "
      "to every pod in the namespace. There are no allow rules to go with it.",
      ["Requests to frontend-proxy time out; new connections between services time out too.",
       "`kubectl get networkpolicy`: `default-deny-ingress` with `podSelector: {}`.",
       "Remove it, or add explicit allow policies before enforcing default-deny."],
      root=["network-policy"]),

    S("proxy-upstream-misroute-042", "service-network", "edge-proxy/upstream-misconfigured",
      "Edge proxy routes shop traffic to the wrong upstream port",
      {"type": "workload_patch", "target": "frontend-proxy", "recreate_pods": False,
       "ops": [env_op("FRONTEND_PORT", "8081")]},
      "The shop returns 503 for every page, while Grafana and Jaeger under the same address still work. "
      "Find the cause and fix it.",
      [J("home"), J("browse")],
      ["kubectl set env deployment/frontend-proxy FRONTEND_PORT=8080", rollout("frontend-proxy")],
      "The Envoy edge proxy builds its routes from environment variables. `FRONTEND_PORT` was set to 8081, "
      "so the shop routes go to `frontend:8081`, where nothing listens. The routes for the other tools are "
      "unaffected.",
      ["`curl -i http://localhost:8080/`: `503 upstream connect error`.",
       "`kubectl logs deploy/frontend-proxy`: upstream connection failures to frontend.",
       "The frontend pod is healthy; `kubectl get deploy frontend-proxy -o yaml`: `FRONTEND_PORT=8081`."],
      root=["frontend-proxy"]),

    # ================================================================== platform
    S("coredns-down-043", "platform", "platform/cluster-dns-down",
      "Cluster DNS scaled to zero",
      {"type": "workload_patch", "namespace": "kube-system", "target": "coredns", "recreate_pods": False,
       "ops": [{"op": "replace", "path": "/spec/replicas", "value": 0}]},
      "New connections across the cluster fail with name-resolution errors; some existing traffic still "
      "works. Find the cause and fix it.",
      [J("home"), J("browse")],
      ["kubectl -n kube-system scale deployment coredns --replicas=2", rollout("coredns", "kube-system")],
      "The CoreDNS Deployment in kube-system was scaled to 0. Nothing in the cluster can resolve names. "
      "Existing long-lived connections keep working, which makes the outage look partial.",
      ["Application logs: `no such host` / `EAI_AGAIN` for service names.",
       "`kubectl -n kube-system get deploy coredns`: 0 replicas; `kubectl -n kube-system get pods -l k8s-app=kube-dns`: none.",
       "Scale it back up."],
      root=["coredns"]),

    S("coredns-rewrite-poison-044", "platform", "platform/cluster-dns-rewrite",
      "CoreDNS rewrite rule sends one service's name to another",
      {"type": "configmap_edit", "namespace": "kube-system", "name": "coredns", "key": "Corefile",
       "replace": [["    ready\n", "    ready\n    rewrite name payment.default.svc.cluster.local "
                                   "shipping.default.svc.cluster.local\n"]],
       "restart_after": ["deployment/coredns"], "recreate_pods_after": ["opentelemetry.io/name=checkout"],
       "settle_s": 25, "restart_on_revert": ["deployment/checkout"]},
      "Payments fail with protocol errors, as if checkout were talking to the wrong service. The payment pod "
      "is healthy. Find the cause and fix it.",
      [J("checkout")],
      ["kubectl -n kube-system get configmap coredns -o yaml | sed '/rewrite name payment.default/d' | "
       "kubectl apply -f -",
       "kubectl -n kube-system rollout restart deployment/coredns", rollout("coredns", "kube-system"),
       "kubectl rollout restart deployment/checkout", rollout("checkout")],
      "Someone added `rewrite name payment.default.svc.cluster.local shipping.default.svc.cluster.local` to "
      "the CoreDNS Corefile. Lookups of `payment` return the shipping Service's IP, so checkout's gRPC calls "
      "reach an HTTP server and fail.",
      ["`kubectl logs deploy/checkout`: protocol / unavailable errors calling payment.",
       "`kubectl run -it --rm dnstest --image=busybox --restart=Never -- nslookup payment`: returns the IP of "
       "the `shipping` Service (compare `kubectl get svc`).",
       "`kubectl -n kube-system get configmap coredns -o yaml`: the rewrite rule."],
      detect=300, root=["coredns"]),

    S("node-cordoned-045", "platform", "platform/nodes-cordoned",
      "All worker nodes cordoned; a pod cannot be rescheduled",
      {"type": "composite", "steps": [
          {"type": "object_patch", "kind": "node", "name": "ai-gym-worker", "namespace": None,
           "ops": [{"op": "set", "path": "/spec/unschedulable", "value": True}]},
          {"type": "object_patch", "kind": "node", "name": "ai-gym-worker2", "namespace": None,
           "ops": [{"op": "set", "path": "/spec/unschedulable", "value": True}],
           "recreate_pods_after": ["opentelemetry.io/name=cart"]}]},
      "The cart went down after its pod was evicted during node maintenance, and it never came back. "
      "Find the cause and fix it.",
      [J("cart"), PODS("cart")],
      ["kubectl uncordon ai-gym-worker ai-gym-worker2", rollout("cart")],
      "Both worker nodes were cordoned for maintenance and never uncordoned. When the cart pod was removed, "
      "its replacement had nowhere to be scheduled (the control-plane node is tainted).",
      ["`kubectl get pods`: cart `Pending`.",
       "`kubectl describe pod -l opentelemetry.io/name=cart`: `node(s) were unschedulable`.",
       "`kubectl get nodes`: both workers `SchedulingDisabled`."],
      root=["nodes"]),

    S("node-taint-046", "platform", "platform/nodes-tainted",
      "Worker nodes tainted; the replacement pod has no toleration",
      {"type": "composite", "steps": [
          {"type": "object_patch", "kind": "node", "name": "ai-gym-worker", "namespace": None,
           "ops": [{"op": "append", "path": "/spec/taints",
                    "value": {"key": "dedicated", "value": "batch", "effect": "NoSchedule"}}]},
          {"type": "object_patch", "kind": "node", "name": "ai-gym-worker2", "namespace": None,
           "ops": [{"op": "append", "path": "/spec/taints",
                    "value": {"key": "dedicated", "value": "batch", "effect": "NoSchedule"}}],
           "recreate_pods_after": ["opentelemetry.io/name=currency"]}]},
      "Currency conversion (and with it checkout) stopped working after its pod was rescheduled. "
      "Find the cause and fix it.",
      [J("currency"), PODS("currency")],
      ["kubectl taint nodes ai-gym-worker ai-gym-worker2 dedicated=batch:NoSchedule-", rollout("currency")],
      "Both workers were tainted `dedicated=batch:NoSchedule` to reserve them for batch jobs. The new "
      "currency pod has no matching toleration and cannot be scheduled anywhere.",
      ["`kubectl get pods`: currency `Pending`.",
       "`kubectl describe pod -l opentelemetry.io/name=currency`: `untolerated taint {dedicated: batch}`.",
       "`kubectl describe nodes | grep Taints`."],
      root=["nodes"]),

    S("quota-blocks-pods-047", "platform", "platform/resource-quota-exhausted",
      "ResourceQuota lower than the namespace's pod count",
      {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=shipping"],
       "manifests": [{"apiVersion": "v1", "kind": "ResourceQuota",
                      "metadata": {"name": "namespace-pod-quota", "namespace": "default"},
                      "spec": {"hard": {"pods": "10"}}}]},
      "Shipping disappeared after a routine pod restart and has not come back; orders fail. "
      "Find the cause and fix it.",
      [J("checkout"), PODS("shipping")],
      ["kubectl delete resourcequota namespace-pod-quota", "kubectl rollout restart deployment/shipping",
       rollout("shipping")],
      "A ResourceQuota caps the namespace at 10 pods while about 25 already run. When the shipping pod was "
      "replaced, the ReplicaSet could not create the new one.",
      ["`kubectl get pods`: no shipping pod at all (not even Pending).",
       "`kubectl describe rs -l opentelemetry.io/name=shipping`: `FailedCreate ... exceeded quota: namespace-pod-quota`.",
       "`kubectl get resourcequota`."],
      root=["resource-quota"]),

    S("limitrange-rejects-048", "platform", "platform/limit-range-rejects",
      "LimitRange max is lower than a container's limit",
      {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=ad"],
       "manifests": [{"apiVersion": "v1", "kind": "LimitRange",
                      "metadata": {"name": "container-memory-cap", "namespace": "default"},
                      "spec": {"limits": [{"type": "Container", "max": {"memory": "128Mi"}}]}}]},
      "The ad service vanished after a restart and never came back. Find the cause and fix it.",
      [J("ads"), PODS("ad")],
      ["kubectl delete limitrange container-memory-cap", "kubectl rollout restart deployment/ad", rollout("ad")],
      "A LimitRange caps any container at 128Mi of memory. The ad container's limit is 300Mi, so admission "
      "rejects the replacement pod.",
      ["`kubectl get pods`: no ad pod.",
       "`kubectl describe rs -l opentelemetry.io/name=ad`: `maximum memory usage per Container is 128Mi, but limit is 300Mi`.",
       "`kubectl get limitrange`."],
      root=["limit-range"]),

    S("pod-security-restricted-049", "platform", "platform/pod-security-admission",
      "Namespace switched to the 'restricted' Pod Security Standard",
      {"type": "object_patch", "kind": "namespace", "name": "default", "namespace": None,
       "recreate_pods_after": ["opentelemetry.io/name=image-provider"],
       "ops": [{"op": "set", "path": "/metadata/labels/pod-security.kubernetes.io~1enforce", "value": "restricted"}]},
      "Product images broke after the image service restarted, and its pod is gone. Find the cause and fix it.",
      [J("images"), PODS("image-provider")],
      ["kubectl label namespace default pod-security.kubernetes.io/enforce-",
       "kubectl rollout restart deployment/image-provider", rollout("image-provider")],
      "The namespace was labelled `pod-security.kubernetes.io/enforce=restricted`. Existing pods keep "
      "running, but any recreated pod that does not meet the restricted profile is rejected at admission.",
      ["`kubectl get pods`: no image-provider pod.",
       "`kubectl describe rs -l opentelemetry.io/name=image-provider`: `violates PodSecurity \"restricted:latest\"`.",
       "`kubectl get namespace default --show-labels`."],
      root=["pod-security"]),

    S("webhook-blocks-pods-050", "platform", "platform/admission-webhook-unavailable",
      "Validating webhook with failurePolicy=Fail and no backend",
      {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=email"],
       "manifests": [{"apiVersion": "admissionregistration.k8s.io/v1", "kind": "ValidatingWebhookConfiguration",
                      "metadata": {"name": "pod-policy-guard"},
                      "webhooks": [{"name": "pods.policy-guard.gym.local", "admissionReviewVersions": ["v1"],
                                    "sideEffects": "None", "failurePolicy": "Fail", "timeoutSeconds": 5,
                                    "clientConfig": {"service": {"namespace": "gym-system", "name": "policy-guard",
                                                                 "port": 443, "path": "/validate"}},
                                    "rules": [{"operations": ["CREATE"], "apiGroups": [""], "apiVersions": ["v1"],
                                               "resources": ["pods"]}],
                                    "namespaceSelector": {"matchLabels": {
                                        "kubernetes.io/metadata.name": "default"}}}]}]},
      "Order confirmation emails stopped after the email pod restarted, and no new email pod appears. "
      "Find the cause and fix it.",
      [J("email"), PODS("email")],
      ["kubectl delete validatingwebhookconfiguration pod-policy-guard",
       "kubectl rollout restart deployment/email", rollout("email")],
      "A ValidatingWebhookConfiguration `pod-policy-guard` intercepts every pod creation in the namespace "
      "with `failurePolicy: Fail`, but its backend service does not exist. Every pod create is rejected.",
      ["`kubectl get pods`: no email pod.",
       "`kubectl describe rs -l opentelemetry.io/name=email`: `failed calling webhook \"pods.policy-guard.gym.local\" ... service \"policy-guard\" not found`.",
       "`kubectl get validatingwebhookconfigurations`."],
      root=["admission-webhook"]),

    S("kube-proxy-stopped-051", "platform", "platform/service-proxy-down",
      "kube-proxy removed; Service rules go stale when a pod moves",
      {"type": "composite", "steps": [
          {"type": "workload_patch", "kind": "daemonset", "namespace": "kube-system", "target": "kube-proxy",
           "recreate_pods": False, "pause_s": 20,
           "ops": [{"op": "set", "path": "/spec/template/spec/nodeSelector/proxy-tier", "value": "disabled"}]},
          {"type": "create_objects", "manifests": [], "recreate_pods_after": ["opentelemetry.io/name=payment"]}]},
      "After the payment pod was restarted, every order fails. The new payment pod is Running and Ready, "
      "and its endpoints look correct. Find the cause and fix it.",
      [J("checkout")],
      [jpatch("daemonset", "kube-proxy",
              '[{"op":"remove","path":"/spec/template/spec/nodeSelector/proxy-tier"}]', "kube-system"),
       "kubectl -n kube-system rollout status daemonset/kube-proxy --timeout=180s"],
      "kube-proxy (which programs Service IPs into node network rules) was removed by a nodeSelector no "
      "node matches. The old rules stay in place, so nothing breaks until an endpoint changes. When payment "
      "got a new pod IP, the `payment` Service kept sending traffic to the old IP.",
      ["Endpoints for `payment` show the new pod IP, yet checkout cannot connect.",
       "`kubectl -n kube-system get pods -l k8s-app=kube-proxy`: none running.",
       "`kubectl -n kube-system get ds kube-proxy -o yaml`: nodeSelector `proxy-tier=disabled`."],
      detect=300, root=["kube-proxy"]),

    # ===================================================================== chaos
    S("net-packet-loss-052", "chaos", "chaos/network-packet-loss",
      "Heavy packet loss on a service's network interface",
      {"type": "chaos_mesh", "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "NetworkChaos",
          "metadata": {"name": "catalog-packet-loss", "namespace": "default"},
          "spec": {"action": "loss", "mode": "all",
                   "selector": {"namespaces": ["default"], "labelSelectors": {"opentelemetry.io/name": "product-catalog"}},
                   "loss": {"loss": "60", "correlation": "0"}, "direction": "to"}}]},
      "Product pages load slowly and sometimes fail; retries sometimes help. Find the cause and fix it.",
      [J("browse", repeat=4, ms=1500), J("catalog", repeat=3, ms=1500)],
      ["kubectl delete networkchaos.chaos-mesh.org catalog-packet-loss"],
      "A Chaos Mesh NetworkChaos experiment drops 60% of packets leaving the product-catalog pod. TCP "
      "retransmits turn that into multi-second latency and occasional timeouts.",
      ["Jaeger: time spent waiting on product-catalog calls, not inside them.",
       "`kubectl get pods`: nothing is crashing.",
       "`kubectl get networkchaos -A`: `catalog-packet-loss`."],
      root=["product-catalog"]),

    S("net-bandwidth-053", "chaos", "chaos/network-bandwidth-limit",
      "Bandwidth throttled to a trickle on the image server",
      {"type": "chaos_mesh", "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "NetworkChaos",
          "metadata": {"name": "images-bandwidth", "namespace": "default"},
          "spec": {"action": "bandwidth", "mode": "all",
                   "selector": {"namespaces": ["default"], "labelSelectors": {"opentelemetry.io/name": "image-provider"}},
                   # tc units: "kbps" = kilobytes per second. At 8kbps images took ~2.6s (vs ~0.2s).
                   "bandwidth": {"rate": "2kbps", "limit": 20971520, "buffer": 10000}, "direction": "to"}}]},
      "Pages load quickly but product images take forever or never appear. Find the cause and fix it.",
      [J("images", ms=1500, timeout=10)],
      ["kubectl delete networkchaos.chaos-mesh.org images-bandwidth"],
      "A NetworkChaos bandwidth experiment limits the image server to 2 kilobytes per second. Small API "
      "responses are barely affected, but images of tens of kilobytes take many seconds to transfer.",
      ["Only large responses are slow; latency grows with response size.",
       "`kubectl get networkchaos -A`: `images-bandwidth`."],
      root=["image-provider"]),

    S("net-partition-054", "chaos", "chaos/network-partition",
      "Network partition between two specific services",
      {"type": "chaos_mesh", "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "NetworkChaos",
          "metadata": {"name": "checkout-payment-partition", "namespace": "default"},
          "spec": {"action": "partition", "mode": "all", "direction": "both",
                   "selector": {"namespaces": ["default"], "labelSelectors": {"opentelemetry.io/name": "checkout"}},
                   "target": {"mode": "all", "selector": {"namespaces": ["default"],
                                                          "labelSelectors": {"opentelemetry.io/name": "payment"}}}}}]},
      "Orders hang and then fail at payment. Payment answers requests from everywhere else. "
      "Find the cause and fix it.",
      [J("checkout")],
      ["kubectl delete networkchaos.chaos-mesh.org checkout-payment-partition"],
      "A NetworkChaos partition drops all traffic between the checkout and payment pods, in both "
      "directions. Each side can still talk to everything else.",
      ["checkout logs: payment calls time out.",
       "A test call to payment from another pod succeeds, so the problem is specific to the checkout-payment path.",
       "`kubectl get networkchaos -A`: `checkout-payment-partition`."],
      root=["checkout", "payment"]),

    S("pod-failure-055", "chaos", "chaos/pod-failure",
      "Pod stays 'Running' but its process has been replaced by a pause container",
      {"type": "chaos_mesh", "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "PodChaos",
          "metadata": {"name": "shipping-pod-failure", "namespace": "default"},
          "spec": {"action": "pod-failure", "mode": "all",
                   "selector": {"namespaces": ["default"], "labelSelectors": {"opentelemetry.io/name": "shipping"}}}}]},
      "Orders fail at shipping. `kubectl get pods` claims shipping is Running. Find the cause and fix it.",
      [J("checkout")],
      ["kubectl delete podchaos.chaos-mesh.org shipping-pod-failure"],
      "A PodChaos `pod-failure` experiment swapped the shipping container's image for a `pause` image, so "
      "the pod exists and looks alive but nothing is serving.",
      ["`kubectl get pods`: shipping Running, but connections to it fail.",
       "`kubectl get pod -l opentelemetry.io/name=shipping -o jsonpath='{.items[0].spec.containers[0].image}'`: "
       "a pause image, not the shipping image.",
       "`kubectl get podchaos -A`: `shipping-pod-failure`."],
      root=["shipping"]),

    S("dns-random-057", "chaos", "chaos/dns-wrong-answers",
      "DNS returns random addresses for one name",
      # DNSChaos needs a shell in the target container; recommendation (python) has one.
      {"type": "chaos_mesh", "kill_pods_after": ["opentelemetry.io/name=product-catalog"], "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "DNSChaos",
          "metadata": {"name": "catalog-dns-random", "namespace": "default"},
          "spec": {"action": "random", "mode": "all", "patterns": ["product-catalog", "product-catalog.*"],
                   "selector": {"namespaces": ["default"],
                                "labelSelectors": {"opentelemetry.io/name": "recommendation"}}}}]},
      "Recommendations have failed since the product-catalog pod was rescheduled; the catalog itself "
      "serves product pages fine. Find the cause and fix it.",
      [J("recommendations", timeout=6)],
      ["kubectl delete dnschaos.chaos-mesh.org catalog-dns-random"],
      "A DNSChaos experiment makes recommendation's DNS lookups of `product-catalog` return random IP "
      "addresses. The lookups succeed, so there is no DNS error, but the connections go nowhere.",
      ["recommendation logs: connection failures / timeouts to odd IP addresses for product-catalog.",
       "`nslookup product-catalog` from another pod returns the correct ClusterIP.",
       "`kubectl get dnschaos -A`: `catalog-dns-random`."],
      root=["recommendation", "dns"]),

    S("http-abort-058", "chaos", "chaos/http-fault-abort",
      "HTTP requests to a service aborted at layer 7",
      {"type": "chaos_mesh", "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "HTTPChaos",
          "metadata": {"name": "email-http-abort", "namespace": "default"},
          "spec": {"mode": "all", "target": "Request", "port": 8080, "path": "*", "abort": True,
                   "selector": {"namespaces": ["default"], "labelSelectors": {"opentelemetry.io/name": "email"}}}}]},
      "Order confirmation emails are no longer being sent; the email pod is Running with no errors in its "
      "logs. Find the cause and fix it.",
      [J("email")],
      ["kubectl delete httpchaos.chaos-mesh.org email-http-abort"],
      "An HTTPChaos experiment aborts every HTTP request to the email service on port 8080, before it "
      "reaches the application. That is why the email app's own logs show nothing.",
      ["checkout logs: sending confirmations fails (connection reset / EOF).",
       "The email app logs show no incoming requests at all.",
       "`kubectl get httpchaos -A`: `email-http-abort`."],
      root=["email"]),

    S("http-replace-059", "chaos", "chaos/http-response-corruption",
      "HTTP responses from a service replaced with garbage",
      {"type": "chaos_mesh", "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "HTTPChaos",
          "metadata": {"name": "quote-http-garbage", "namespace": "default"},
          "spec": {"mode": "all", "target": "Response", "port": 8080, "path": "*",
                   "replace": {"body": "bm90LWEtbnVtYmVy", "code": 200},
                   "selector": {"namespaces": ["default"], "labelSelectors": {"opentelemetry.io/name": "quote"}}}}]},
      "Orders fail at the shipping step with parse errors, yet the quote service returns HTTP 200. "
      "Find the cause and fix it.",
      [J("checkout")],
      ["kubectl delete httpchaos.chaos-mesh.org quote-http-garbage"],
      "An HTTPChaos experiment rewrites every response from the quote service to the body `not-a-number` "
      "with status 200. Shipping cannot parse the quote, so checkout fails, though every HTTP status is OK.",
      ["shipping logs: failed to parse the quote response.",
       "Calling quote directly from a debug pod returns `not-a-number` instead of a price.",
       "`kubectl get httpchaos -A`: `quote-http-garbage`."],
      root=["quote"]),

    S("jvm-exception-062", "chaos", "chaos/jvm-method-exception",
      "Exception injected into a JVM method at runtime",
      {"type": "chaos_mesh", "manifest": [{
          "apiVersion": "chaos-mesh.org/v1alpha1", "kind": "JVMChaos",
          "metadata": {"name": "ad-getads-exception", "namespace": "default"},
          "spec": {"action": "exception", "mode": "all",
                   "class": "oteldemo.AdService$AdServiceImpl", "method": "getAds",
                   # Byteman can only throw checked exceptions a method declares; getAds declares none.
                   "exception": "java.lang.RuntimeException(\"ad inventory unavailable\")", "port": 9277,
                   "selector": {"namespaces": ["default"], "labelSelectors": {"opentelemetry.io/name": "ad"}}}}]},
      "The ad banner is gone and the ad service logs mention an inventory error, although no one deployed "
      "anything. Find the cause and fix it.",
      [J("ads")],
      ["kubectl delete jvmchaos.chaos-mesh.org ad-getads-exception"],
      "A Chaos Mesh JVMChaos experiment attached a Byteman agent to the running ad JVM and makes "
      "`AdServiceImpl.getAds` throw `RuntimeException(\"ad inventory unavailable\")`. The code on disk is "
      "unchanged.",
      ["ad logs: `RuntimeException: ad inventory unavailable` from getAds.",
       "No new deploy: `kubectl rollout history deployment/ad`.",
       "`kubectl get jvmchaos -A`: `ad-getads-exception`."],
      root=["ad"]),

    # ============================================================ application flags
    S("flag-ad-failure-064", "application", "app-flag/ad-failure",
      "Ad service fails every request (feature flag adFailure)",
      {"type": "feature_flag", "flag": "adFailure", "variant": "on"},
      "The ad banner is missing on some page views, and the frontend logs occasional errors from the ad "
      "service. Find the cause and fix it.",
      # adFailure fails ~1 in 10 requests: 30 probes catch it ~96% of the time.
      [J("ads", repeat=30)],
      ["python injectors/toggle_flag.py adFailure --off"],
      "The `adFailure` feature flag is on, so the ad service fails about one in ten GetAds calls on "
      "purpose. The failure is intermittent, so small samples often look healthy.",
      ["ad logs: errors on some GetAds calls; frontend `/api/data` returns 500 now and then.",
       "Error rate over many requests is ~10%, not 100%.",
       "Nothing restarted and nothing was deployed.",
       "Feature Flags UI: `adFailure` is on."],
      root=["ad"]),

    S("flag-ad-high-cpu-065", "application", "app-flag/ad-high-cpu",
      "Ad service burns CPU on every request (adHighCpu)",
      {"type": "feature_flag", "flag": "adHighCpu", "variant": "on"},
      "The ad service's CPU usage has spiked far above normal and ad responses are slow. "
      "Find the cause and fix it.",
      [{"type": "cpu_usage", "selector": "opentelemetry.io/name=ad", "max_cores": 0.5}, J("ads", ms=1000)],
      ["python injectors/toggle_flag.py adHighCpu --off"],
      "The `adHighCpu` flag makes the ad service run a CPU-heavy loop on requests, which saturates its CPU.",
      ["Grafana / kubelet stats: ad container CPU far above baseline.",
       "Jaeger: GetAds spans are long, with an attribute showing the high-CPU path.",
       "Feature Flags UI: `adHighCpu` is on."],
      detect=300, root=["ad"]),

    S("flag-ad-manual-gc-066", "application", "app-flag/ad-full-gc",
      "Ad service triggers full garbage collections (adManualGc)",
      # The JVM can stay wedged after the flag is off (run 5: ads still timing out 5 min later),
      # so both the fix and the revert restart it.
      {"type": "feature_flag", "flag": "adManualGc", "variant": "on", "restart_on_revert": ["deployment/ad"]},
      "Ad requests show long, irregular latency spikes. Find the cause and fix it.",
      [J("ads", repeat=4, ms=700)],
      ["python injectors/toggle_flag.py adManualGc --off", "kubectl rollout restart deployment/ad",
       rollout("ad")],
      "The `adManualGc` flag makes the ad service fill its heap with throwaway objects and force full "
      "`System.gc()` runs, causing long stop-the-world pauses. The JVM can stay stuck in garbage collection "
      "after the flag is turned off, so the service also needs a restart.",
      ["Jaeger: GetAds spans have long gaps inside the service.",
       "JVM metrics (Grafana): GC pause time spikes; heap usage pinned near its maximum.",
       "ad logs: `Triggering a manual garbage collection` / `The artificially triggered GCs took ... ms`.",
       "Feature Flags UI: `adManualGc` is on."],
      detect=300, root=["ad"]),

    S("flag-cart-failure-067", "application", "app-flag/cart-failure",
      "Cart service errors (cartFailure)",
      {"type": "feature_flag", "flag": "cartFailure", "variant": "100%"},
      "Customers report errors around their cart and when placing orders. Find the cause and fix it.",
      [J("cart"), J("checkout")],
      ["python injectors/toggle_flag.py cartFailure --off"],
      "The `cartFailure` flag (at 100%) makes the cart service fail its operations on purpose.",
      ["cart logs / Jaeger: cart RPC errors carrying the feature-flag attribute.",
       "Pods are healthy, and valkey-cart is healthy.",
       "Feature Flags UI: `cartFailure` is at 100%."],
      root=["cart"]),

    S("flag-email-memory-leak-068", "application", "app-flag/email-memory-leak",
      "Email service leaks memory until it is OOMKilled (emailMemoryLeak)",
      {"type": "feature_flag", "flag": "emailMemoryLeak", "variant": "10000x"},
      "The email service restarts every few minutes and some confirmations are lost. Find the cause and fix it.",
      [STABLE("email", 300), J("email")],
      ["python injectors/toggle_flag.py emailMemoryLeak --off", "kubectl rollout restart deployment/email",
       rollout("email")],
      "The `emailMemoryLeak` flag makes the email service keep a growing copy of data for every email, so "
      "its memory climbs until it is OOMKilled at its 100Mi limit, over and over.",
      ["`kubectl describe pod -l opentelemetry.io/name=email`: `Last State: OOMKilled`, restart count rising.",
       "Memory graph: sawtooth.",
       "Feature Flags UI: `emailMemoryLeak` is on. Turn it off, then restart to drop the leaked memory."],
      detect=900, recover=600, baseline=400, hold=45, poll=15, root=["email"]),

    S("flag-image-slow-load-071", "application", "app-flag/image-slow-load",
      "Images served with an artificial delay (imageSlowLoad)",
      {"type": "feature_flag", "flag": "imageSlowLoad", "variant": "10sec"},
      "Product images take about 10 seconds to appear. Find the cause and fix it.",
      [J("images_browser", ms=3000, timeout=15)],
      ["python injectors/toggle_flag.py imageSlowLoad --off"],
      "The `imageSlowLoad` flag is read by the shop's browser code, which then sends every image request "
      "with `x-envoy-fault-delay-request: 10000`. The Envoy edge proxy honours that header and holds each "
      "image for 10 seconds. The image server itself is fast.",
      ["Only image requests are slow; the rest of each page is fast.",
       "The browser dev tools / frontend-proxy logs: image requests carry `x-envoy-fault-delay-request`; "
       "image-provider's own response time is milliseconds.",
       "Feature Flags UI: `imageSlowLoad` is at 10sec."],
      root=["image-provider"]),

    S("flag-intl-shipping-slow-072", "application", "app-flag/intl-shipping-slowdown",
      "International shipping quotes delayed (intlShippingSlowdown)",
      {"type": "feature_flag", "flag": "intlShippingSlowdown", "variant": "10sec"},
      "Customers outside the US say placing an order takes forever; US customers are fine. "
      "Find the cause and fix it.",
      [J("checkout_intl", repeat=2, ms=5000, timeout=20)],
      ["python injectors/toggle_flag.py intlShippingSlowdown --off"],
      "The `intlShippingSlowdown` flag makes shipping delay quotes for non-US addresses by 10 seconds. It "
      "only affects some customers, so aggregate latency barely moves.",
      ["Jaeger: shipping spans are ~10s only for orders with a non-US address.",
       "US orders are fast.",
       "Feature Flags UI: `intlShippingSlowdown` is at 10sec."],
      root=["shipping"]),

    S("flag-flood-homepage-073", "application", "app-flag/traffic-flood",
      "Synthetic traffic flood against the homepage (loadGeneratorFloodHomepage)",
      {"type": "feature_flag", "flag": "loadGeneratorFloodHomepage", "variant": "on"},
      "Homepage traffic jumped far above normal and the frontend's CPU went with it, yet there were no "
      "releases or marketing campaigns. Find the source and stop it.",
      [{"type": "traffic", "match": "^/$", "window_s": 30, "max_error_pct": 100, "max_avg_ms": 100000,
        "min_requests": 0, "max_rps": 2.0}],
      ["python injectors/toggle_flag.py loadGeneratorFloodHomepage --off"],
      "The `loadGeneratorFloodHomepage` flag makes the load generator send 100 homepage requests per "
      "task, an internal traffic flood that looks like an attack.",
      ["frontend-proxy access logs / Locust stats: homepage request rate far above normal, all from the "
       "load generator.",
       "Feature Flags UI: `loadGeneratorFloodHomepage` is on."],
      detect=180, root=["load-generator"]),

    S("obs-pii-redaction-removed-069", "observability", "observability/telemetry-redaction-removed",
      "PII reaches the tracing backend after the redaction step was removed from the pipeline",
      {"type": "composite", "steps": [
          # Background: the services emit raw personal data in span attributes.
          {"type": "feature_flag", "flag": "emitRawPii", "variant": "on"},
          # The actual incident: the collector pipeline no longer scrubs it.
          {"type": "configmap_edit", "name": "otel-collector-agent", "key": "relay",
           "replace": [["      - transform/redact_sensitive_data\n", ""], ["      - redaction\n", ""]],
           "restart_after": ["daemonset/otel-collector-agent"]}]},
      "Compliance alert: plain-text customer email addresses and full card numbers were found in trace data "
      "in Jaeger. Find how they got there and stop the leak.",
      [J("checkout", repeat=2, ms=5000),
       {"type": "jaeger_attr_absent", "service": "checkout", "lookback": "2m",
        "pattern": "@example\\.com|\\b\\d{4}-\\d{4}-\\d{4}-\\d{4}\\b"},
       {"type": "jaeger_attr_absent", "service": "payment", "lookback": "2m",
        "pattern": "@example\\.com|\\b\\d{4}-\\d{4}-\\d{4}-\\d{4}\\b"}],
      ["kubectl get configmap otel-collector-agent -o yaml > /tmp/relay.yaml && "
       "python3 -c \"import sys,yaml; d=yaml.safe_load(open('/tmp/relay.yaml')); c=yaml.safe_load(d['data']['relay']); "
       "p=c['service']['pipelines']['traces']['processors']; "
       "[p.append(x) for x in ('transform/redact_sensitive_data','redaction') if x not in p]; "
       "d['data']['relay']=yaml.safe_dump(c); "
       "[d['metadata'].pop(k,None) for k in ('resourceVersion','uid','creationTimestamp','managedFields')]; "
       "yaml.safe_dump(d, open('/tmp/relay.yaml','w'))\" && kubectl apply -f /tmp/relay.yaml",
       "kubectl rollout restart daemonset/otel-collector-agent",
       "kubectl rollout status daemonset/otel-collector-agent --timeout=180s"],
      "The services attach raw personal data (customer email, full card number) to spans. Normally the "
      "collector's `transform/redact_sensitive_data` and `redaction` processors hash or mask these "
      "attributes before export. They were removed from the traces pipeline, so the raw values now "
      "reach Jaeger.",
      ["Jaeger: checkout/payment spans carry `user.email` and `demo.payment.card_number` in clear text.",
       "`kubectl get cm otel-collector-agent -o yaml`: the traces pipeline's processors list lacks "
       "`transform/redact_sensitive_data` and `redaction`, although both processors are still defined.",
       "Restore them in the pipeline and restart the collector. In reality, also purge the leaked data "
       "and investigate why apps emit raw PII (here: the `emitRawPii` flag)."],
      detect=300, recover=360, root=["otel-collector"]),

    # ============================================================ datastores / runtime
    S("valkey-maxmemory-075", "datastore", "datastore/kv-memory-cap-noeviction",
      "Valkey memory cap reached with 'noeviction' -> writes rejected",
      {"type": "exec_commands", "target": "deploy/valkey-cart",
       # 256kb is below even an empty instance's footprint, so every write is refused.
       "commands": [["valkey-cli", "CONFIG", "SET", "maxmemory", "256kb"]],
       "undo_commands": [["valkey-cli", "CONFIG", "SET", "maxmemory", "0"]]},
      "Customers can view their carts but adding an item fails. Find the cause and fix it.",
      [J("cart")],
      ["kubectl exec deploy/valkey-cart -- valkey-cli CONFIG SET maxmemory 0"],
      "Valkey's `maxmemory` was set to 256kb, below the memory it already uses, while `maxmemory-policy` is "
      "`noeviction`. Reads work; every write fails with `OOM command not allowed when used memory > 'maxmemory'`.",
      ["cart logs: `OOM command not allowed` on writes.",
       "`kubectl exec deploy/valkey-cart -- valkey-cli INFO memory`: used_memory > maxmemory, policy noeviction.",
       "Raise or remove the cap (or allow eviction)."],
      root=["valkey-cart"]),

    S("valkey-requirepass-076", "datastore", "datastore/kv-credential-mismatch",
      "Valkey password set; the client does not know it",
      {"type": "exec_commands", "target": "deploy/valkey-cart", "restart_after": ["deployment/cart"],
       "commands": [["valkey-cli", "CONFIG", "SET", "requirepass", "rotated-s3cret"]],
       "undo_commands": [["valkey-cli", "-a", "rotated-s3cret", "--no-auth-warning", "CONFIG", "SET",
                          "requirepass", ""]]},
      "Since the cart service restarted, every cart operation fails with an authentication error. "
      "Find the cause and fix it.",
      [J("cart")],
      ["kubectl exec deploy/valkey-cart -- valkey-cli -a rotated-s3cret --no-auth-warning CONFIG SET requirepass ''",
       "kubectl rollout restart deployment/cart", rollout("cart")],
      "Someone set `requirepass` on valkey-cart. Already-open connections kept working, but after cart "
      "restarted it connected without a password and got `NOAUTH Authentication required`.",
      ["cart logs: `NOAUTH Authentication required`.",
       "`kubectl exec deploy/valkey-cart -- valkey-cli PING`: `NOAUTH`.",
       "Either remove the password or give cart the credential; the reference fix removes the "
       "unauthorised change."],
      root=["valkey-cart"]),

    S("valkey-client-pause-077", "datastore", "datastore/kv-clients-paused",
      "Valkey clients paused -> writes hang",
      {"type": "exec_commands", "target": "deploy/valkey-cart",
       "commands": [["valkey-cli", "CLIENT", "PAUSE", "86400000", "WRITE"]],
       "undo_commands": [["valkey-cli", "CLIENT", "UNPAUSE"]]},
      "Adding to cart spins forever and then times out; viewing the cart still works. Find the cause and fix it.",
      [J("cart", timeout=6)],
      ["kubectl exec deploy/valkey-cart -- valkey-cli CLIENT UNPAUSE"],
      "A `CLIENT PAUSE ... WRITE` was issued on valkey-cart (typically left over from a failover or "
      "maintenance script), so every write command blocks while reads continue.",
      ["cart logs: timeouts on writes only.",
       "`kubectl exec deploy/valkey-cart -- valkey-cli INFO clients`: clients blocked; `CLIENT LIST` shows "
       "paused writes.",
       "`CLIENT UNPAUSE` releases them."],
      root=["valkey-cart"]),

    S("pg-revoked-grant-078", "datastore", "datastore/db-permission-revoked",
      "Database role lost SELECT on the table the service reads",
      {"type": "exec_commands", "target": "deploy/astronomy-db",
       "commands": [["psql", "-U", "postgres", "-d", "astronomy_db", "-c",
                     "REVOKE SELECT ON catalog.products FROM astronomy_user"]],
       "undo_commands": [["psql", "-U", "postgres", "-d", "astronomy_db", "-c",
                          "GRANT SELECT ON catalog.products TO astronomy_user"]]},
      "The product catalog returns errors on every page, right after a database permissions audit. "
      "Find the cause and fix it.",
      [J("browse"), J("catalog")],
      ["kubectl exec deploy/astronomy-db -- psql -U postgres -d astronomy_db -c "
       "'GRANT SELECT ON catalog.products TO astronomy_user'"],
      "The audit revoked `SELECT` on `catalog.products` from `astronomy_user`, the role product-catalog "
      "connects as. Every query fails with `permission denied for table products`.",
      ["product-catalog logs: `permission denied for table products`.",
       "`psql ... -c '\\dp catalog.products'`: astronomy_user has no SELECT.",
       "Re-grant the privilege."],
      root=["astronomy-db"]),

    S("pg-password-rotated-079", "datastore", "datastore/db-credential-rotation",
      "Database password rotated without updating the clients",
      {"type": "exec_commands", "target": "deploy/astronomy-db",
       "commands": [["psql", "-U", "postgres", "-c", "ALTER ROLE astronomy_user PASSWORD 'rotated-2026'"],
                    ["psql", "-U", "postgres", "-c",
                     "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename='astronomy_user'"]],
       "undo_commands": [["psql", "-U", "postgres", "-c",
                          "ALTER ROLE astronomy_user PASSWORD 'astronomy_password'"]]},
      "After a database maintenance window, product pages fail and new orders are not being recorded. "
      "Find the cause and fix it.",
      [J("browse"), J("catalog")],
      ["kubectl exec deploy/astronomy-db -- psql -U postgres -c "
       "\"ALTER ROLE astronomy_user PASSWORD 'astronomy_password'\""],
      "`astronomy_user`'s password was rotated in Postgres and existing sessions were terminated, but "
      "product-catalog and accounting still use the old password from their configuration. Every "
      "reconnect fails authentication.",
      ["product-catalog logs: `password authentication failed for user \"astronomy_user\"`.",
       "The database is up; other roles can log in.",
       "Either roll the password back or update the clients' secret. The reference fix restores the "
       "password the apps are configured with."],
      root=["astronomy-db"]),

    S("pg-connection-limit-080", "datastore", "datastore/db-connection-limit",
      "Role connection limit set to zero",
      {"type": "exec_commands", "target": "deploy/astronomy-db",
       "commands": [["psql", "-U", "postgres", "-c", "ALTER ROLE astronomy_user CONNECTION LIMIT 0"],
                    ["psql", "-U", "postgres", "-c",
                     "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename='astronomy_user'"]],
       "undo_commands": [["psql", "-U", "postgres", "-c", "ALTER ROLE astronomy_user CONNECTION LIMIT -1"]]},
      "Product pages fail with database errors, but the database is up and the password is correct. "
      "Find the cause and fix it.",
      [J("browse"), J("catalog")],
      ["kubectl exec deploy/astronomy-db -- psql -U postgres -c 'ALTER ROLE astronomy_user CONNECTION LIMIT -1'"],
      "`astronomy_user` was given `CONNECTION LIMIT 0` (an attempt to drain the role before maintenance) "
      "and its sessions were terminated. Reconnects are rejected with `too many connections for role`.",
      ["product-catalog logs: `too many connections for role \"astronomy_user\"`.",
       "`psql -c \"select rolname, rolconnlimit from pg_roles\"`: connlimit 0.",
       "Set it back to -1 (unlimited)."],
      root=["astronomy-db"]),

    S("pg-lock-held-081", "datastore", "datastore/db-lock-held",
      "A stuck maintenance job holds an exclusive table lock",
      {"type": "create_objects", "manifests": [{
          "apiVersion": "apps/v1", "kind": "Deployment",
          "metadata": {"name": "catalog-maintenance", "namespace": "default", "labels": {"app": "catalog-maintenance"}},
          "spec": {"replicas": 1, "selector": {"matchLabels": {"app": "catalog-maintenance"}},
                   "template": {"metadata": {"labels": {"app": "catalog-maintenance"}},
                                "spec": {"containers": [{
                                    "name": "reindex", "image": "postgres:18.4",
                                    "env": [{"name": "PGPASSWORD", "value": "changeit"}],
                                    "command": ["psql", "-h", "astronomy-db", "-U", "postgres", "-d", "astronomy_db",
                                                "-c", "BEGIN; LOCK TABLE catalog.products IN ACCESS EXCLUSIVE MODE; "
                                                      "SELECT pg_sleep(86400);"],
                                    "resources": {"limits": {"memory": "64Mi"}}}]}}}}]},
      "Product pages hang until they time out; the database is up and not busy. Find the cause and fix it.",
      [J("browse", timeout=6), J("catalog", timeout=6)],
      ["kubectl delete deployment catalog-maintenance"],
      "A `catalog-maintenance` job opened a transaction and took an ACCESS EXCLUSIVE lock on "
      "`catalog.products`, then got stuck. Every product query waits behind the lock.",
      ["product-catalog: queries hang (no error, just timeouts).",
       "`psql -c \"select pid, state, query, wait_event_type from pg_stat_activity\"`: product queries "
       "waiting on a Lock; one session idle in transaction holding it.",
       "`kubectl get pods`: `catalog-maintenance` is the lock holder. Stop it (or `pg_terminate_backend`)."],
      root=["astronomy-db"]),

    S("kafka-message-too-large-082", "datastore", "datastore/queue-message-size-limit",
      "Topic max message size below the size of real messages",
      {"type": "exec_commands", "target": "deploy/gym-kafka-tools", "namespace": "gym-system",
       "restart_on_revert": ["deployment/checkout", "deployment/accounting", "deployment/fraud-detection"],
       "commands": [["/opt/kafka/bin/kafka-configs.sh", "--bootstrap-server", "kafka.default.svc.cluster.local:9092",
                     "--alter", "--entity-type", "topics", "--entity-name", "orders",
                     "--add-config", "max.message.bytes=128"]],
       "undo_commands": [["/opt/kafka/bin/kafka-configs.sh", "--bootstrap-server",
                          "kafka.default.svc.cluster.local:9092", "--alter", "--entity-type", "topics",
                          "--entity-name", "orders", "--delete-config", "max.message.bytes"]]},
      "Checkout works, but no new orders reach accounting or fraud detection. Find the cause and fix it.",
      [ORDERS, J("checkout", repeat=2, ms=5000)],
      ["kubectl exec -n gym-system deploy/gym-kafka-tools -- /opt/kafka/bin/kafka-configs.sh --bootstrap-server "
       "kafka.default.svc.cluster.local:9092 --alter --entity-type topics --entity-name orders "
       "--delete-config max.message.bytes"],
      "The `orders` topic got `max.message.bytes=128`. Every order event is larger, so the broker rejects "
      "it (`RecordTooLargeException`). Checkout publishes asynchronously and only logs the error, so orders "
      "succeed while the downstream consumers receive nothing.",
      ["checkout logs: producer errors `The request included a message larger than the max message size`.",
       "Consumer lag is not growing (nothing is produced), which rules out slow consumers.",
       "`kafka-configs.sh --describe --entity-type topics --entity-name orders`: max.message.bytes=128."],
      root=["kafka"]),

    S("kafka-broker-down-083", "datastore", "datastore/message-broker-down",
      "Message broker scaled to zero (async pipeline stops silently)",
      {"type": "workload_patch", "target": "kafka", "recreate_pods": False,
       "restart_on_revert": ["deployment/checkout", "deployment/accounting", "deployment/fraud-detection"],
       "revert_hooks": [{"kafka_topic": "orders"}],
       "ops": [{"op": "replace", "path": "/spec/replicas", "value": 0}]},
      "Accounting has recorded no new orders for a while, and placing orders has started to time out. "
      "Find the cause and fix it.",
      [ORDERS, PODS("kafka")],
      ["kubectl scale deployment kafka --replicas=1", rollout("kafka"), KAFKA_TOPIC_FIX,
       "kubectl rollout restart deployment/checkout deployment/accounting deployment/fraud-detection",
       rollout("checkout"), rollout("accounting"), rollout("fraud-detection")],
      "The Kafka Deployment was scaled to zero. The consumers (accounting, fraud-detection) sit "
      "disconnected, and checkout's Kafka producer gets stuck, so orders eventually time out too.",
      ["accounting logs: `brokers are down`; checkout requests time out.",
       "`kubectl get deploy kafka`: 0 replicas.",
       "After restoring the broker, recreate the `orders` topic (no persistent volume in this demo) and "
       "restart checkout and the consumers; they do not recover on their own."],
      recover=480, root=["kafka"]),

    # ================================================================ observability
    S("otel-exporter-broken-085", "observability", "observability/collector-exporter-misconfigured",
      "Collector exports traces to the wrong port",
      {"type": "configmap_edit", "name": "otel-collector-agent", "key": "relay",
       "replace": [["endpoint: jaeger:4317", "endpoint: jaeger:4999"]],
       "restart_after": ["daemonset/otel-collector-agent"]},
      "No new traces have appeared in Jaeger for any service since a telemetry config change. "
      "Find the cause and fix it.",
      [TRACES("checkout"), TRACES("frontend")],
      ["kubectl get configmap otel-collector-agent -o yaml | sed 's/jaeger:4999/jaeger:4317/' | kubectl apply -f -",
       "kubectl rollout restart daemonset/otel-collector-agent",
       "kubectl rollout status daemonset/otel-collector-agent --timeout=180s"],
      "The collector config's `otlp_grpc/jaeger` exporter endpoint was changed to `jaeger:4999`, where "
      "nothing listens. Every trace batch fails to export and is dropped.",
      ["collector logs: `Exporting failed ... jaeger:4999 ... connection refused`.",
       "Jaeger is up, but its newest traces are minutes old.",
       "`kubectl get cm otel-collector-agent -o yaml`: the exporter endpoint."],
      detect=300, root=["otel-collector"]),

    S("otel-collector-unscheduled-086", "observability", "observability/collector-not-running",
      "Collector DaemonSet has a nodeSelector that matches no node",
      {"type": "workload_patch", "kind": "daemonset", "target": "otel-collector-agent", "recreate_pods": False,
       "ops": [{"op": "set", "path": "/spec/template/spec/nodeSelector/telemetry-tier", "value": "dedicated"}]},
      "All telemetry stopped at once: no new traces, and metrics have gone flat. Find the cause and fix it.",
      [PODS("collector", selector=COLLECTOR), TRACES("frontend")],
      [jpatch("daemonset", "otel-collector-agent",
              '[{"op":"remove","path":"/spec/template/spec/nodeSelector/telemetry-tier"}]'),
       "kubectl rollout status daemonset/otel-collector-agent --timeout=180s"],
      "The collector DaemonSet now requires nodes labelled `telemetry-tier=dedicated`. No node has that "
      "label, so the DaemonSet runs zero pods and every service's telemetry export fails.",
      ["`kubectl get ds otel-collector-agent`: DESIRED 0.",
       "Service logs: OTLP export errors to otel-collector.",
       "`kubectl get ds otel-collector-agent -o yaml`: the nodeSelector."],
      detect=300, root=["otel-collector"]),

    S("otel-service-endpoint-087", "observability", "observability/service-exporter-misconfigured",
      "One service exports telemetry to a collector name that does not exist",
      {"type": "workload_patch", "target": "checkout", "recreate_pods": False,
       "ops": [env_op("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector-gateway:4318")]},
      "Checkout's spans are missing from every trace (traces jump from the frontend straight to payment "
      "and shipping). Find the cause and fix it.",
      [TRACES("checkout")],
      ["kubectl set env deployment/checkout 'OTEL_EXPORTER_OTLP_ENDPOINT=http://$(OTEL_COLLECTOR_NAME):4318'",
       rollout("checkout")],
      "Checkout's `OTEL_EXPORTER_OTLP_ENDPOINT` points at `otel-collector-gateway`, which does not exist. "
      "Only checkout's telemetry is lost, which leaves gaps in otherwise healthy traces.",
      ["Jaeger: no traces for service `checkout`, while others are fine.",
       "checkout logs: OTLP export errors resolving `otel-collector-gateway`.",
       "`kubectl get deploy checkout -o yaml`: the endpoint."],
      detect=300, root=["checkout"]),

    S("prometheus-otlp-disabled-088", "observability", "observability/metrics-ingest-disabled",
      "Prometheus restarted without its OTLP receiver",
      {"type": "workload_patch", "target": "prometheus", "recreate_pods": False,
       "ops": [{"op": "replace", "path": "/spec/template/spec/containers/$c/args",
                "value": ["--storage.tsdb.retention.time=7d", "--config.file=/etc/config/prometheus.yml",
                          "--storage.tsdb.path=/data", "--web.console.libraries=/etc/prometheus/console_libraries",
                          "--web.console.templates=/etc/prometheus/consoles", "--enable-feature=exemplar-storage"]}]},
      "Every metrics dashboard went flat after Prometheus was restarted with 'cleaned up' flags. "
      "Find the cause and fix it.",
      [{"type": "prometheus", "query": "sum(rate(http_server_request_duration_seconds_count[1m]))", "min_value": 0.01}],
      [jpatch("deployment", "prometheus", '[{"op":"add","path":"/spec/template/spec/containers/0/args/-",'
                                          '"value":"--web.enable-otlp-receiver"}]'),
       "kubectl rollout status deployment/prometheus --timeout=240s"],
      "Prometheus was restarted without `--web.enable-otlp-receiver`. The collector pushes metrics over "
      "OTLP, and every push is now rejected (404), so no new samples arrive.",
      ["collector logs: `Exporting failed ... prometheus ... 404`.",
       "Prometheus is up, but queries for application metrics return nothing recent.",
       "`kubectl get deploy prometheus -o yaml`: the OTLP receiver flag is missing."],
      detect=300, recover=360, root=["prometheus"]),

    S("grafana-datasource-089", "observability", "observability/dashboard-datasource-misconfigured",
      "Grafana's Prometheus datasource points at the wrong port",
      # No restarts: the grafana-sc-datasources sidecar watches ConfigMaps labelled grafana_datasource and
      # calls Grafana's provisioning reload API, so edits apply live (~15s).
      {"type": "configmap_edit", "name": "grafana-datasources", "key": "default.yaml",
       "replace": [["url: http://prometheus:9090", "url: http://prometheus:9099"]]},
      "Every Grafana dashboard shows 'No data', while Prometheus itself answers queries fine. "
      "Find the cause and fix it.",
      [{"type": "http", "url": "http://grafana.default.svc.cluster.local/grafana/api/datasources/uid/"
                               "webstore-metrics/health", "expect_status": 200, "contains": "\"status\":\"OK\"",
        "max_ms": 10000}],
      ["kubectl get configmap grafana-datasources -o yaml | sed 's|prometheus:9099|prometheus:9090|' | "
       "kubectl replace -f -"],
      "The provisioned Prometheus datasource URL was changed to port 9099, where nothing listens, so "
      "Grafana's queries time out while Prometheus and the data are fine. The datasource sidecar applies "
      "ConfigMap edits to Grafana live, so fixing the ConfigMap is enough; no restart is needed.",
      ["Grafana > Connections > Data sources > Prometheus > Test: the query to :9099 times out.",
       "`kubectl get cm grafana-datasources -o yaml`: the URL.",
       "`kubectl logs deploy/grafana -c grafana-sc-datasources`: it wrote the new file and Grafana reloaded it.",
       "Prometheus answers on :9090 directly."],
      detect=300, recover=300, root=["grafana"],
      notes="An earlier version restarted Grafana on inject and fix. The verifier then failed only because "
            "Grafana itself was down, and each rolling restart briefly ran two 4-container Grafana pods, "
            "which thrashed the 6 GB VM late in long batches."),

    # ================================================================== compound
    S("compound-quota-blocks-fix-090", "compound", "compound/fix-blocked-by-quota",
      "Broken config plus a quota that blocks the rollout of the fix",
      {"type": "composite", "steps": [
          {"type": "workload_patch", "target": "shipping", "recreate_pods": False,
           "ops": [env_op("QUOTE_ADDR", "http://quote-svc:8080")], "pause_s": 25},
          {"type": "create_objects",
           "manifests": [{"apiVersion": "v1", "kind": "ResourceQuota",
                          "metadata": {"name": "namespace-pod-quota", "namespace": "default"},
                          "spec": {"hard": {"pods": "10"}}}]}]},
      "Orders fail at shipping. The obvious config fix was applied, but the rollout never completes. "
      "Find the cause and fix it for real.",
      [J("checkout")],
      ["kubectl delete resourcequota namespace-pod-quota",
       "kubectl set env deployment/shipping QUOTE_ADDR=http://quote:8080", rollout("shipping")],
      "Two problems. Shipping's `QUOTE_ADDR` points at `quote-svc`, which does not exist. And a ResourceQuota "
      "caps the namespace at 10 pods (about 25 already run), so the corrected Deployment's new pod cannot "
      "be created: the rollout stalls and the broken pod keeps serving.",
      ["shipping logs: cannot resolve `quote-svc`.",
       "After fixing the env var: `kubectl rollout status` hangs; `kubectl describe rs` shows "
       "`exceeded quota: namespace-pod-quota`.",
       "Remove/raise the quota, then the fix rolls out."],
      root=["shipping", "resource-quota"]),

    S("compound-two-faults-091", "compound", "compound/independent-simultaneous-faults",
      "Two unrelated faults at the same time",
      {"type": "composite", "steps": [
          {"type": "workload_patch", "target": "recommendation", "recreate_pods": False,
           "ops": [env_op("PRODUCT_CATALOG_ADDR", "product-catalog:8081")]},
          {"type": "feature_flag", "flag": "adFailure", "variant": "on"}]},
      "Two complaints came in within minutes: recommendations are missing, and the ad banner keeps "
      "disappearing. Find the cause(s) and fix everything.",
      [J("recommendations"), J("ads", repeat=30)],
      ["kubectl set env deployment/recommendation PRODUCT_CATALOG_ADDR=product-catalog:8080",
       rollout("recommendation"), "python injectors/toggle_flag.py adFailure --off"],
      "Two independent root causes: recommendation's `PRODUCT_CATALOG_ADDR` uses the wrong port (8081), "
      "and the `adFailure` flag is on. Fixing one leaves the other broken; the verifier requires both.",
      ["recommendation logs: connection refused to product-catalog:8081.",
       "ad logs / Feature Flags UI: `adFailure` on.",
       "Do not stop after the first fix; re-check both symptoms."],
      root=["recommendation", "ad"]),

    S("compound-red-herring-092", "compound", "compound/red-herring",
      "A loud but irrelevant failing pod next to the real, quieter fault",
      {"type": "composite", "steps": [
          {"type": "create_objects", "manifests": [{
              "apiVersion": "apps/v1", "kind": "Deployment",
              "metadata": {"name": "legacy-report-generator", "namespace": "default",
                           "labels": {"app": "legacy-report-generator"}},
              "spec": {"replicas": 1, "selector": {"matchLabels": {"app": "legacy-report-generator"}},
                       "template": {"metadata": {"labels": {"app": "legacy-report-generator"}},
                                    "spec": {"containers": [{
                                        "name": "report", "image": "busybox:latest",
                                        "command": ["sh", "-c", "echo 'FATAL: cannot connect to reporting-db:5432 "
                                                                "(connection refused)'; exit 1"],
                                        "resources": {"limits": {"memory": "16Mi"}}}]}}}}]},
          {"type": "workload_patch", "target": "quote", "recreate_pods": False,
           "ops": [{"op": "replace", "path": "/spec/replicas", "value": 0}]}]},
      "Orders are failing. The on-call channel is full of alerts about a crash-looping pod that keeps "
      "logging database connection errors. Find the real cause and fix it.",
      [J("checkout")],
      ["kubectl scale deployment quote --replicas=1", rollout("quote")],
      "The crash-looping `legacy-report-generator` is a red herring: it is broken but nothing depends on "
      "it. The orders fail because the quote Deployment was scaled to zero, so shipping cannot get quotes.",
      ["Start from the failing request: checkout logs point at shipping, and shipping logs point at quote.",
       "`kubectl get deploy quote`: 0 replicas.",
       "The report generator's logs mention a database nothing else uses."],
      root=["quote"]),
]


# Candidates that were implemented and tested but dropped, because an outside-evidence
# verifier cannot observe them in this environment (kept here so they are not re-added).
DROPPED = {
    "app-flag/db-lock-contention": "productCatalogLockContention showed no user-visible latency change, even "
                                   "with 12 concurrent requests (~300ms both ways). It is aimed at continuous "
                                   "profiling, which is disabled here.",
}
