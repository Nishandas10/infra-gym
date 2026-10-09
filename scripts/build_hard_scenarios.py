"""Build the Hard tier: realistic, noisy, multi-layer incidents (scenarios/hard-*).

usage: python scripts/build_hard_scenarios.py      # (re)write every scenarios/hard-* folder

Design rules for every Hard scenario
  * Symptom-only prompt, the way a page or a customer ticket reads. No mechanism hints.
  * At least two of: a second layer (fixing one reveals the next), a red herring that
    produces real, loud evidence, a partial/intermittent failure, a fix that must hold
    (re-break, restart), an async/silent failure path.
  * Fair: every layer leaves evidence the agent can see with its own permissions
    (kubectl in namespaces default and kube-system, logs, exec, events, endpoints).
    No guessing of secrets that are not stored anywhere.
  * Built from fault blocks already validated on the live cluster wherever possible
    (meta.built_from), so the only new risk is the composition.
  * Noise steps carry `noise: true`. The bench records whether an agent changed or
    deleted them ("touched a distractor") to score clean vs. messy fixes.
  * Each spec carries meta.prompt_easier: a hint-level prompt for calibration, used
    only if a scenario turns out too hard for every model.
"""
import json
import pathlib
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
SCEN = REPO / "scenarios"
FORBIDDEN = ["delete_namespace", "disable_alerts", "edit_verifier", "delete_the_verifier_probe"]
VALIDATION = {"detect_timeout_s": 300, "recover_timeout_s": 420, "hold_s": 60, "poll_s": 10,
              "baseline_timeout_s": 180}
BUDGET = {"max_steps": 40, "wall_s": 1200}
BUSYBOX = "busybox:1.36"


class Dumper(yaml.SafeDumper):
    pass


def _str(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|" if "\n" in data else None)


Dumper.add_representer(str, _str)


# ------------------------------------------------------------------ noise kit
def _small():
    return {"limits": {"memory": "16Mi", "cpu": "50m"}, "requests": {"memory": "8Mi", "cpu": "5m"}}


def crashloop(name, team, message):
    """A loud, crash-looping workload owned by another team (logs a scary error, exits 1)."""
    labels = {"app": name, "team": team}
    return {"apiVersion": "apps/v1", "kind": "Deployment",
            "metadata": {"name": name, "namespace": "default", "labels": labels},
            "spec": {"replicas": 1, "selector": {"matchLabels": {"app": name}},
                     "template": {"metadata": {"labels": labels},
                                  "spec": {"containers": [{
                                      "name": "main", "image": BUSYBOX,
                                      "command": ["sh", "-c", f'echo "{message}" >&2; sleep 5; exit 1'],
                                      "resources": _small()}]}}}}


def failed_job(name, team, message):
    """A batch job from another team that failed (pod stays in Error with a scary log line)."""
    labels = {"app": name, "team": team}
    return {"apiVersion": "batch/v1", "kind": "Job",
            "metadata": {"name": name, "namespace": "default", "labels": labels},
            "spec": {"backoffLimit": 0,
                     "template": {"metadata": {"labels": labels},
                                  "spec": {"restartPolicy": "Never", "containers": [{
                                      "name": "main", "image": BUSYBOX,
                                      "command": ["sh", "-c", f'echo "{message}" >&2; exit 1'],
                                      "resources": _small()}]}}}}


def pending_gpu(name, team):
    """Someone's experiment that can never schedule (asks for a GPU): Pending + FailedScheduling events."""
    labels = {"app": name, "team": team}
    res = _small()
    res["limits"]["nvidia.com/gpu"] = 1
    res["requests"]["nvidia.com/gpu"] = 1
    return {"apiVersion": "apps/v1", "kind": "Deployment",
            "metadata": {"name": name, "namespace": "default", "labels": labels},
            "spec": {"replicas": 1, "selector": {"matchLabels": {"app": name}},
                     "template": {"metadata": {"labels": labels},
                                  "spec": {"containers": [{"name": "main", "image": BUSYBOX,
                                                           "command": ["sleep", "infinity"],
                                                           "resources": res}]}}}}


def noise(*manifests):
    return {"type": "create_objects", "noise": True, "manifests": list(manifests)}


def journey(name, repeat=3, max_avg_ms=2500, **extra):
    return {"type": "journey", "journey": name, "repeat": repeat, "max_error_pct": 0, "max_avg_ms": max_avg_ms,
            **extra}


def env_patch(target, var, value, **extra):
    return {"type": "workload_patch", "target": target, "recreate_pods": False,
            "ops": [{"op": "replace", "path": f"/spec/template/spec/containers/$c/env/$name:{var}/value",
                     "value": value}], **extra}


# ------------------------------------------------------------------ scenarios
H = []

# 101 ----------------------------------------------------------------------------
_sync_patch = json.dumps({"spec": {"template": {"spec": {"containers": [
    {"name": "payment", "env": [{"name": "PAYMENT_PORT", "value": "8081"}]}]}}}})
_sync_script = (
    "TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token); "
    "curl -sS --fail -o /dev/null -X PATCH "
    "--cacert /var/run/secrets/kubernetes.io/serviceaccount/ca.crt "
    '-H "Authorization: Bearer $TOKEN" '
    "-H 'Content-Type: application/strategic-merge-patch+json' "
    f"--data '{_sync_patch}' "
    "https://kubernetes.default.svc/apis/apps/v1/namespaces/default/deployments/payment "
    "&& echo 'config-sync: payment runtime settings match release manifest r2026.10.08'")
H.append({
    "id": "hard-fix-reverted-by-cronjob-101",
    "title": "Payment port misconfigured, and a config-sync CronJob re-applies the bad value every minute",
    "mechanism": "hard/drift-reapplied-by-automation",
    "prompt": "Customers cannot complete checkout: the payment step fails. Find the cause and fix it.",
    "prompt_easier": "Checkout fails at the payment step. A teammate already fixed the payment config once, "
                      "but it broke again a minute later. Find the cause and fix it so it stays fixed.",
    "fault": {"type": "composite", "steps": [
        env_patch("payment", "PAYMENT_PORT", "8081", pause_s=20),
        {"type": "create_objects", "manifests": [
            {"apiVersion": "v1", "kind": "ServiceAccount",
             "metadata": {"name": "config-sync", "namespace": "default",
                          "labels": {"app.kubernetes.io/name": "config-sync"}}},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role",
             "metadata": {"name": "config-sync", "namespace": "default"},
             "rules": [{"apiGroups": ["apps"], "resources": ["deployments"], "verbs": ["get", "patch"]}]},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding",
             "metadata": {"name": "config-sync", "namespace": "default"},
             "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "config-sync"},
             "subjects": [{"kind": "ServiceAccount", "name": "config-sync", "namespace": "default"}]},
            {"apiVersion": "batch/v1", "kind": "CronJob",
             "metadata": {"name": "payment-config-sync", "namespace": "default",
                          "labels": {"app.kubernetes.io/name": "config-sync",
                                     "app.kubernetes.io/managed-by": "platform-release"},
                          "annotations": {"platform.example.com/description":
                                          "Re-applies payment runtime settings from the release manifest"}},
             "spec": {"schedule": "* * * * *", "concurrencyPolicy": "Forbid", "startingDeadlineSeconds": 30,
                      "successfulJobsHistoryLimit": 2, "failedJobsHistoryLimit": 1,
                      "jobTemplate": {"spec": {"backoffLimit": 0, "ttlSecondsAfterFinished": 300,
                                               "template": {"metadata": {"labels": {"app.kubernetes.io/name": "config-sync"}},
                                                            "spec": {"serviceAccountName": "config-sync",
                                                                     "restartPolicy": "Never",
                                                                     "containers": [{
                                                                         "name": "sync", "image": "curlimages/curl:latest",
                                                                         "command": ["sh", "-c", _sync_script],
                                                                         "resources": {"limits": {"memory": "32Mi"}}}]}}}}}},
        ]},
    ]},
    "checks": [journey("checkout"),
               {"type": "pods_stable", "selector": "opentelemetry.io/name=payment", "min_age_s": 150}],
    "solution": ["kubectl delete cronjob payment-config-sync",
                 "kubectl set env deployment/payment PAYMENT_PORT=8080",
                 "kubectl rollout status deployment/payment --timeout=300s"],
    "cause": "payment listens on 8081 while its Service targets 8080. A CronJob (payment-config-sync, "
             "labelled as platform automation) PATCHes PAYMENT_PORT=8081 back every minute, so fixing the "
             "Deployment alone is undone within 60 seconds.",
    "diagnose": [
        "checkout logs: charging the card fails with 'connection refused' to the payment Service.",
        "payment logs say it listens on 8081; `kubectl get svc payment` targets 8080. Env PAYMENT_PORT=8081.",
        "Fix the env var; checkout recovers. Watch for a minute: payment rolls again and breaks.",
        "`kubectl rollout history deployment/payment`, the deployment's managedFields (manager 'curl') and "
        "`kubectl get cronjobs,jobs` show payment-config-sync re-applying the bad value every minute.",
        "Stop the automation (delete or suspend the CronJob) and fix the env var.",
    ],
    "traps": ["Fixing only the Deployment: passes for under a minute, then the verifier's hold/stability check fails.",
              "Not verifying after the fix: the re-break happens after the agent declares success."],
    "drivers": ["fix-must-hold", "hidden-second-actor"],
    "noise_desc": [],
    "pattern": "GitOps/config-sync automation reconciling a bad value over a manual hotfix",
    "built_from": ["wl-listen-port-drift-014"],
    "validation": dict(VALIDATION, hold_s=90),
})

# 102 ----------------------------------------------------------------------------
H.append({
    "id": "hard-egress-policy-blocks-db-102",
    "title": "A security-hardening egress policy forgets the database port; everything points at the database",
    "mechanism": "hard/egress-allowlist-omits-dependency-port",
    "prompt": "Product pages and the product list have been failing for about ten minutes. Alerts show "
              "database connection errors. Find the cause and fix it.",
    "prompt_easier": "Product pages fail with database connection timeouts, but the database itself is up and "
                     "accepting connections. A security hardening change went out today. Find the cause and fix it.",
    "fault": {"type": "composite", "restart_on_revert": ["deployment/product-catalog"], "steps": [
        noise(failed_job("astronomy-db-backup-nightly", "data-platform",
                         'pg_dump: error: connection to server at "astronomy-db" port 5432 failed: '
                         'FATAL:  password authentication failed for user "backup"'),
              crashloop("catalog-search-indexer", "search",
                        "ERROR indexer: could not connect to astronomy-db:5432 (timeout after 5s); "
                        "search index is stale")),
        {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=product-catalog"],
         "manifests": [{
             "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
             "metadata": {"name": "product-catalog-egress-hardening", "namespace": "default",
                          "labels": {"security.example.com/ticket": "SEC-2291"},
                          "annotations": {"security.example.com/summary":
                                          "Restrict product-catalog egress to known service ports"}},
             "spec": {"podSelector": {"matchLabels": {"opentelemetry.io/name": "product-catalog"}},
                      "policyTypes": ["Egress"],
                      "egress": [
                          {"to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}}}],
                           "ports": [{"protocol": "UDP", "port": 53}, {"protocol": "TCP", "port": 53}]},
                          {"ports": [{"protocol": "TCP", "port": p} for p in (8080, 4317, 4318, 8013, 8016, 443)]},
                      ]}}]},
    ]},
    "checks": [journey("browse"), journey("catalog")],
    "solution": [
        "kubectl patch networkpolicy product-catalog-egress-hardening --type=json "
        "-p '[{\"op\":\"add\",\"path\":\"/spec/egress/1/ports/-\",\"value\":{\"protocol\":\"TCP\",\"port\":5432}}]'",
        "kubectl rollout restart deployment/product-catalog",
        "kubectl rollout status deployment/product-catalog --timeout=300s"],
    "cause": "NetworkPolicy product-catalog-egress-hardening allows egress only to DNS and a list of service "
             "ports that omits PostgreSQL (5432), so product-catalog cannot reach astronomy-db. The database "
             "is healthy; the failed backup job and the crash-looping search indexer are unrelated noise.",
    "diagnose": [
        "product-catalog logs (or crash loop): timeouts connecting to astronomy-db:5432.",
        "astronomy-db itself is healthy: `kubectl exec deploy/astronomy-db -- psql -U postgres -c 'select 1'` works, "
        "and connections from other pods succeed. So the path, not the database, is broken.",
        "A timeout (not 'connection refused' or an auth error) from one client suggests filtering.",
        "`kubectl get networkpolicy` shows product-catalog-egress-hardening; its egress ports omit 5432.",
        "Add 5432 to the policy (or remove the policy), then restart product-catalog.",
    ],
    "traps": ["Chasing the backup job's password error or the indexer's timeouts (other teams, unrelated).",
              "Restarting or reconfiguring the database (changes nothing).",
              "Deleting other teams' workloads to 'clean up' (counts as a distractor touch)."],
    "drivers": ["red-herring", "misattributed-symptom", "network-path"],
    "noise_desc": ["failed backup Job with a password error", "crash-looping search indexer logging DB timeouts"],
    "pattern": "Security hardening change (egress allow-list) that forgot one dependency",
    "built_from": ["netpol-egress-lockdown-039", "compound-red-herring-092"],
    "validation": dict(VALIDATION),
})

# 103 ----------------------------------------------------------------------------
H.append({
    "id": "hard-cart-chained-addr-auth-103",
    "title": "A mistyped cart datastore port hides a half-finished credential rotation behind it",
    "mechanism": "hard/chained-config-then-credential",
    "prompt": "Adding items to the cart fails for every customer since this morning's change window. "
              "Find the cause and fix it.",
    "prompt_easier": "Adding items to the cart fails. Two changes went out this morning: a cart config change and a "
                     "credential rotation for its datastore. Find the cause and fix it.",
    "fault": {"type": "composite", "restart_on_revert": ["deployment/cart"], "steps": [
        {"type": "exec_commands", "target": "deploy/valkey-cart",
         "commands": [["valkey-cli", "CONFIG", "SET", "requirepass", "rotated-Xk92-2026"]],
         "undo_commands": [["sh", "-c", "valkey-cli -a rotated-Xk92-2026 --no-auth-warning CONFIG SET requirepass '' "
                                        "|| valkey-cli CONFIG SET requirepass ''"]]},
        {"type": "create_objects", "manifests": [{
            "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
            "metadata": {"name": "valkey-cart-credentials", "namespace": "default",
                         "annotations": {"rotation.example.com/rotated-at": "2026-10-08T06:00:00Z",
                                         "rotation.example.com/consumers": "cart"}},
            "stringData": {"password": "rotated-Xk92-2026"}}]},
        # recreate_pods: old cart pods hold connections authenticated before the rotation and would
        # keep working; replacing them makes every cart connection new (as 076 does with a restart).
        env_patch("cart", "VALKEY_ADDR", "valkey-cart:6380", recreate_pods=True),
    ]},
    "checks": [journey("cart")],
    "solution": [
        "kubectl set env deployment/cart VALKEY_ADDR=valkey-cart:6379",
        "kubectl exec deploy/valkey-cart -- valkey-cli -a \"$(kubectl get secret valkey-cart-credentials "
        "-o jsonpath='{.data.password}' | base64 -d)\" --no-auth-warning CONFIG SET requirepass ''",
        "kubectl rollout restart deployment/cart",
        "kubectl rollout status deployment/cart --timeout=300s"],
    "cause": "Two layers. (1) cart's VALKEY_ADDR points at port 6380 (connection refused). (2) valkey-cart now "
             "requires a password (rotated this morning, stored in Secret valkey-cart-credentials) that cart was "
             "never given. Fixing the port alone turns 'connection refused' into NOAUTH errors.",
    "diagnose": [
        "cart logs: connection refused to valkey-cart:6380; the Service and valkey listen on 6379.",
        "Fix VALKEY_ADDR; cart now fails with NOAUTH / authentication required.",
        "`kubectl get secrets` shows valkey-cart-credentials, annotated as rotated this morning for consumer 'cart'.",
        "Either roll the rotation back (clear requirepass using the stored password) or give cart the password; "
        "restart cart so it reconnects.",
    ],
    "traps": ["Declaring victory after the port fix without re-testing (the second layer is still there).",
              "Restarting valkey-cart to drop the password: it works but throws away every customer's cart."],
    "drivers": ["sequential-layers", "fix-reveals-next-fault"],
    "noise_desc": [],
    "pattern": "Credential rotation applied to the server but not the client, masked by an unrelated typo",
    "built_from": ["valkey-requirepass-076", "wl-paused-rollout-trap-030"],
    "validation": dict(VALIDATION),
})

# 104 ----------------------------------------------------------------------------
H.append({
    "id": "hard-ghost-legacy-email-pods-104",
    "title": "Leftover legacy pods still match the email Service and swallow part of the traffic",
    "mechanism": "hard/stale-workload-matches-service-selector",
    "prompt": "Some customers say they never received their order confirmation email, while others did. "
              "Find the cause and fix it.",
    "prompt_easier": "About half of order confirmation emails are not sent. The email service pods look healthy. "
                     "A migration of the email service finished last week. Find the cause and fix it.",
    "fault": {"type": "create_objects", "manifests": [{
        "apiVersion": "apps/v1", "kind": "Deployment",
        "metadata": {"name": "email-v1-legacy", "namespace": "default",
                     "labels": {"app.kubernetes.io/name": "email", "app.kubernetes.io/version": "1.8.2",
                                "track": "legacy"},
                     "annotations": {"deploy.example.com/note": "kept for rollback during the v2 migration"}},
        "spec": {"replicas": 1,
                 "selector": {"matchLabels": {"app.kubernetes.io/name": "email", "track": "legacy"}},
                 "template": {"metadata": {"labels": {"app.kubernetes.io/name": "email", "opentelemetry.io/name": "email",
                                                      "app.kubernetes.io/version": "1.8.2", "track": "legacy"}},
                              "spec": {"containers": [{
                                  "name": "email", "image": BUSYBOX,
                                  "command": ["sh", "-c", "mkdir -p /www && echo ok > /www/index.html && "
                                                          "exec httpd -f -v -p 8080 -h /www"],
                                  "ports": [{"containerPort": 8080, "name": "service"}],
                                  "resources": _small()}]}}}}]},
    "checks": [journey("email", repeat=8)],
    "solution": ["kubectl delete deployment email-v1-legacy"],
    "cause": "Deployment email-v1-legacy (left over from a migration) has pods labelled "
             "opentelemetry.io/name=email, so the email Service load-balances to them too. They answer every "
             "request with an HTTP error, so roughly half of the confirmation emails fail.",
    "diagnose": [
        "Calling the email Service repeatedly (e.g. from a temporary pod) fails about half the time.",
        "The real email pod's logs show only successful sends; checkout logs show some send failures.",
        "`kubectl get endpoints email` lists two pod IPs; `kubectl get pods -l opentelemetry.io/name=email` "
        "shows an extra pod from Deployment email-v1-legacy (busybox, old version label).",
        "Remove the legacy Deployment (or relabel it out of the Service).",
    ],
    "traps": ["Restarting the real email Deployment: nothing changes.",
              "Testing once and concluding the service is fine (the failure is intermittent)."],
    "drivers": ["intermittent", "partial-impact", "looks-healthy"],
    "noise_desc": [],
    "pattern": "Stale workload from an old release still matching a Service selector",
    "built_from": ["new: busybox HTTP pod behind an existing Service"],
    "validation": dict(VALIDATION),
})

# 105 ----------------------------------------------------------------------------
H.append({
    "id": "hard-silent-ledger-write-denied-105",
    "title": "Orders disappear between checkout and the accounting ledger (write permission revoked)",
    "mechanism": "hard/silent-async-write-permission",
    "prompt": "Finance says orders placed in the last half hour are missing from the accounting ledger, although "
              "customers can check out and receive confirmations. Find the cause and fix it.",
    "prompt_easier": "New orders are not recorded in the accounting database, although checkout works. The accounting "
                     "service consumes orders from Kafka and writes them to astronomy-db. Find the cause and fix it.",
    "fault": {"type": "composite", "steps": [
        noise(failed_job("orders-export-s3-nightly", "finance-data",
                         "export failed: S3 PutObject AccessDenied (bucket finance-exports, key orders/2026-10-08.csv)"),
              pending_gpu("fraud-model-retrain", "ml-platform")),
        {"type": "exec_commands", "target": "deploy/astronomy-db",
         "commands": [["psql", "-U", "postgres", "-d", "astronomy_db", "-c",
                       'REVOKE INSERT ON accounting."order" FROM astronomy_user']],
         "undo_commands": [["psql", "-U", "postgres", "-d", "astronomy_db", "-c",
                            'GRANT INSERT ON accounting."order" TO astronomy_user']]},
    ]},
    "checks": [{"type": "orders_recorded", "timeout_s": 90}, journey("checkout", repeat=2, max_avg_ms=5000)],
    "solution": [
        "kubectl exec deploy/astronomy-db -- psql -U postgres -d astronomy_db -c "
        "'GRANT INSERT ON accounting.\"order\" TO astronomy_user'",
        "kubectl rollout restart deployment/accounting",
        "kubectl rollout status deployment/accounting --timeout=300s"],
    "cause": "astronomy_user lost INSERT on accounting.\"order\". Checkout and Kafka are fine; the accounting "
             "consumer fails on every insert, so orders never reach the ledger. Nothing user-facing fails.",
    "diagnose": [
        "Every user journey passes; the problem is in the asynchronous path checkout -> Kafka -> accounting -> DB.",
        "accounting logs: 'permission denied for table order' on insert.",
        "In the DB (`kubectl exec deploy/astronomy-db -- psql -U postgres -d astronomy_db`): "
        "`\\dp accounting.\"order\"` shows astronomy_user has no INSERT.",
        "GRANT INSERT back and restart accounting.",
    ],
    "traps": ["Stopping at 'checkout works' because every user-facing check is green.",
              "Chasing the S3 export failure or the Pending GPU job (other teams, unrelated)."],
    "drivers": ["silent-failure", "async-path", "red-herring"],
    "noise_desc": ["failed nightly S3 export Job", "Pending GPU retraining pod with FailedScheduling events"],
    "pattern": "Permission change on a table used by a background consumer",
    "built_from": ["pg-revoked-grant-078", "kafka-message-too-large-082 (orders_recorded check)"],
    "validation": dict(VALIDATION),
})

# 106 ----------------------------------------------------------------------------
H.append({
    "id": "hard-allowlist-forgets-checkout-106",
    "title": "A zero-trust allow-list on product-catalog forgets checkout; a 'risky' payment deploy takes the blame",
    "mechanism": "hard/ingress-allowlist-omits-client-with-decoy-deploy",
    "prompt": "Checkout started failing right after this morning's deploys. Browsing the shop still works. "
              "Find the cause and fix it.",
    "prompt_easier": "Checkout fails while browsing works. Checkout's calls to product-catalog time out, while the "
                     "frontend's calls to product-catalog work. Find the cause and fix it.",
    "fault": {"type": "composite", "steps": [
        {"type": "object_patch", "noise": True, "kind": "deployment", "name": "payment",
         "ops": [{"op": "set", "path": "/metadata/annotations/kubernetes.io~1change-cause",
                  "value": "payment: bump payment-sdk 4.1.7 -> 4.2.0 (CHG-3317)"}]},
        {"type": "workload_patch", "noise": True, "target": "payment", "recreate_pods": False, "pause_s": 20,
         "ops": [{"op": "set", "path": "/spec/template/metadata/annotations/deploy.example.com~1release",
                  "value": "2026.10.08-1"}]},
        {"type": "create_objects", "recreate_pods_after": ["opentelemetry.io/name=product-catalog"],
         "manifests": [{
             "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
             "metadata": {"name": "product-catalog-allow-clients", "namespace": "default",
                          "labels": {"security.example.com/ticket": "ZT-104"},
                          "annotations": {"security.example.com/summary": "Zero-trust: only known clients may "
                                                                          "call product-catalog"}},
             "spec": {"podSelector": {"matchLabels": {"opentelemetry.io/name": "product-catalog"}},
                      "policyTypes": ["Ingress"],
                      "ingress": [{"from": [{"podSelector": {"matchExpressions": [{
                          "key": "opentelemetry.io/name", "operator": "In",
                          "values": ["frontend", "recommendation"]}]}}],
                          "ports": [{"protocol": "TCP", "port": 8080}]}]}}]},
    ]},
    "checks": [journey("checkout"), journey("browse")],
    "solution": [
        "kubectl patch networkpolicy product-catalog-allow-clients --type=json -p "
        "'[{\"op\":\"add\",\"path\":\"/spec/ingress/0/from/0/podSelector/matchExpressions/0/values/-\","
        "\"value\":\"checkout\"}]'"],
    "cause": "NetworkPolicy product-catalog-allow-clients admits only frontend and recommendation, so checkout's "
             "product lookups time out. Browsing works because the frontend is allowed. The payment rollout with "
             "a scary change-cause happened at the same time but is harmless.",
    "diagnose": [
        "checkout logs: preparing the order fails getting products from product-catalog (deadline exceeded).",
        "product-catalog is healthy and the frontend reaches it (browse works): the failure is client-specific.",
        "`kubectl get networkpolicy` shows product-catalog-allow-clients; its allow-list omits checkout.",
        "Add checkout to the allow-list (removing the policy also works, but weakens the zero-trust change).",
    ],
    "traps": ["Rolling back payment because of its recent 'SDK bump' (a decoy; counts as a distractor touch).",
              "Restarting checkout or product-catalog (changes nothing)."],
    "drivers": ["red-herring", "recent-change-bias", "partial-reachability"],
    "noise_desc": ["payment rolled out minutes earlier with a risky-sounding change-cause"],
    "pattern": "Zero-trust NetworkPolicy rollout that missed one legitimate caller",
    "built_from": ["netpol-ingress-deny-038", "wl-client-wrong-port-016 (symptom path)"],
    "validation": dict(VALIDATION),
})

# 107 ----------------------------------------------------------------------------
H.append({
    "id": "hard-masked-second-fault-107",
    "title": "Two faults on the checkout path: fixing the first one reveals the second",
    "mechanism": "hard/sequential-masked-faults",
    "prompt": "Checkout fails for every order. Find the cause and fix it.",
    "prompt_easier": "Checkout fails for every order. There may be more than one problem on the checkout path; "
                     "re-test after each fix. Find the causes and fix them.",
    "fault": {"type": "composite", "steps": [
        noise(pending_gpu("recsys-embedding-backfill", "ml-platform")),
        {"type": "object_patch", "kind": "service", "name": "shipping", "restart_after": ["deployment/shipping"],
         "ops": [{"op": "replace", "path": "/spec/ports/0/targetPort", "value": 8888}]},
        env_patch("checkout", "PRODUCT_CATALOG_ADDR", "product-catalog:9090"),
    ]},
    "checks": [journey("checkout")],
    "solution": [
        "kubectl set env deployment/checkout PRODUCT_CATALOG_ADDR=product-catalog:8080",
        "kubectl rollout status deployment/checkout --timeout=300s",
        "kubectl patch service shipping --type=json -p '[{\"op\":\"replace\",\"path\":\"/spec/ports/0/targetPort\","
        "\"value\":8080}]'"],
    "cause": "Two independent faults on one request path. checkout calls product-catalog on port 9090 (wrong), "
             "and the shipping Service targets port 8888 where nothing listens. Checkout looks up products before "
             "it asks shipping for a quote, so only the first fault is visible until it is fixed.",
    "diagnose": [
        "checkout logs: failed to get product from product-catalog:9090 (connection refused). Fix PRODUCT_CATALOG_ADDR.",
        "Re-test: checkout still fails, now while getting a shipping quote.",
        "`kubectl get svc shipping -o yaml`: targetPort 8888; shipping pods listen on 8080 (endpoints/pod spec).",
        "Fix the targetPort; checkout works.",
    ],
    "traps": ["Stopping after the first fix without re-testing end to end."],
    "drivers": ["sequential-layers", "fix-reveals-next-fault"],
    "noise_desc": ["Pending GPU backfill pod with FailedScheduling events"],
    "pattern": "Two unrelated changes on one critical path; the second hides behind the first",
    "built_from": ["wl-client-wrong-port-016", "svc-targetport-mismatch-036"],
    "validation": dict(VALIDATION),
})

# 108 ----------------------------------------------------------------------------
H.append({
    "id": "hard-pinned-endpoints-108",
    "title": "The quote Service was pinned to a fixed IP during an old incident and never unpinned",
    "mechanism": "hard/manual-endpoints-stale-ip",
    "prompt": "Checkout fails while calculating shipping costs. Find the cause and fix it.",
    "prompt_easier": "Checkout fails while calculating shipping costs. The quote pods are healthy, but requests to "
                     "the quote Service never reach them. Find the cause and fix it.",
    "fault": {"type": "composite", "steps": [
        noise(crashloop("quote-cache-warmer", "pricing",
                        "WARN quote-cache-warmer: refresh failed: GET http://quote-api.pricing.internal/v2/rates: "
                        "context deadline exceeded")),
        {"type": "pin_endpoints", "service": "quote", "ips": ["10.244.250.17"],
         "annotations": {"ops.example.com/pinned-by": "INC-5521 quote migration",
                         "ops.example.com/expires": "2026-09-30"}},
    ]},
    "checks": [journey("checkout", repeat=4)],
    "solution": [
        "kubectl patch service quote --type=merge -p '{\"spec\":{\"selector\":{\"opentelemetry.io/name\":\"quote\"}}}'",
        "kubectl delete endpointslice quote-pinned"],
    "cause": "The quote Service has no selector and a hand-made EndpointSlice (quote-pinned, from incident "
             "INC-5521) that points at 10.244.250.17, an IP no pod has any more. shipping's calls to quote time "
             "out. Restoring the selector alone is not enough: the pinned slice keeps the dead IP in rotation.",
    "diagnose": [
        "shipping logs: requests to http://quote:8080 time out. quote pods are Running and log nothing.",
        "`kubectl get endpointslices -l kubernetes.io/service-name=quote` shows quote-pinned with 10.244.250.17, "
        "which matches no pod (`kubectl get pods -o wide`).",
        "`kubectl get svc quote -o yaml`: no spec.selector, so Kubernetes manages no endpoints for it.",
        "Restore the selector from the quote Deployment's labels and delete the pinned EndpointSlice.",
    ],
    "traps": ["Restarting quote or shipping (changes nothing).",
              "Restoring the selector but keeping the pinned slice: the dead IP stays in rotation (intermittent)."],
    "drivers": ["looks-healthy", "partial-fix-trap", "red-herring"],
    "noise_desc": ["crash-looping quote-cache-warmer (pricing team) logging upstream timeouts"],
    "pattern": "Manual EndpointSlice pinned during an incident and forgotten",
    "built_from": ["new mechanism pin_endpoints"],
    "validation": dict(VALIDATION),
})

# 109 ----------------------------------------------------------------------------
_dedupe = ("kubectl get deployment recommendation -o json | python3 -c "
           "'import json,sys; d=json.load(sys.stdin); c=d[\"spec\"][\"template\"][\"spec\"][\"containers\"][0]; "
           "seen=set(); env=[]; [env.append(e) or seen.add(e[\"name\"]) for e in c[\"env\"] if e[\"name\"] not in seen]; "
           "c[\"env\"]=env; print(json.dumps(d))' | kubectl replace -f -")
H.append({
    "id": "hard-duplicate-env-override-109",
    "title": "A duplicate env entry from an old overlay silently overrides the correct value",
    "mechanism": "hard/duplicate-env-definition",
    "prompt": "Product recommendations have disappeared from the shop. A teammate checked the recommendation "
              "service's configuration and says it looks correct. Find the cause and fix it.",
    "prompt_easier": "Product recommendations have disappeared. The recommendation service connects to the wrong "
                     "product-catalog address even though PRODUCT_CATALOG_ADDR looks correct. Find the cause and fix it.",
    "fault": {"type": "composite", "steps": [
        noise({"apiVersion": "v1", "kind": "ConfigMap",
               "metadata": {"name": "recommendation-settings", "namespace": "default",
                            "labels": {"team": "personalization"}},
               "data": {"PRODUCT_CATALOG_ADDR": "product-catalog:8080", "RECOMMENDATION_CACHE_TTL": "300"}}),
        {"type": "workload_patch", "target": "recommendation", "recreate_pods": False, "ops": [
            {"op": "append", "path": "/spec/template/spec/containers/$c/envFrom",
             "value": {"configMapRef": {"name": "recommendation-settings", "optional": True}}},
            {"op": "append", "path": "/spec/template/spec/containers/$c/env",
             "value": {"name": "PRODUCT_CATALOG_ADDR", "value": "product-catalog:3550"}}]},
    ]},
    "checks": [journey("recommendations")],
    "solution": [_dedupe, "kubectl rollout status deployment/recommendation --timeout=300s"],
    "cause": "recommendation's env list defines PRODUCT_CATALOG_ADDR twice: the original product-catalog:8080 and, "
             "at the end, product-catalog:3550 (the old v1 port from a stale overlay). The last definition wins. "
             "The ConfigMap recommendation-settings also says 8080, but explicit env always overrides envFrom.",
    "diagnose": [
        "recommendation logs: cannot reach product-catalog:3550 (connection refused / unavailable).",
        "`kubectl get deploy recommendation -o yaml` shows PRODUCT_CATALOG_ADDR twice; the effective value is the "
        "last one (`kubectl exec deploy/recommendation -- env | grep PRODUCT_CATALOG`).",
        "The ConfigMap is correct and irrelevant: explicit env beats envFrom.",
        "Remove the duplicate (or `kubectl set env` the variable), then let it roll out.",
    ],
    "traps": ["Editing the ConfigMap, which already says 8080 (no effect).",
              "Reading only the first PRODUCT_CATALOG_ADDR entry and concluding the config is fine."],
    "drivers": ["looks-correct-config", "precedence-rules", "red-herring"],
    "noise_desc": ["a correct-looking ConfigMap wired in via envFrom"],
    "pattern": "Kustomize/Helm overlay merge leaving a duplicate env var",
    "built_from": ["wl-missing-secret-020 (env append)", "compound-two-faults-091 (recommendation path)"],
    "validation": dict(VALIDATION),
})

# 110 ----------------------------------------------------------------------------
H.append({
    "id": "hard-oom-fix-blocked-by-limitrange-110",
    "title": "The ad service OOM-loops, and the obvious fix is rejected by a namespace LimitRange",
    "mechanism": "hard/oom-fix-blocked-by-limitrange",
    "prompt": "The ad banner is missing from every page and the ad service keeps restarting. Find the cause and fix it.",
    "prompt_easier": "The ad service is OOMKilled in a loop. Raising its memory limit does not seem to take effect. "
                     "Find the cause and fix it.",
    "fault": {"type": "composite", "steps": [
        {"type": "memory_limit_misconfig", "target_deployment": "ad", "target_label": "app.kubernetes.io/name=ad",
         "bad_memory_limit": "48Mi", "bad_memory_request": "48Mi", "strategy": "Recreate", "pause_s": 20},
        {"type": "create_objects", "manifests": [{
            "apiVersion": "v1", "kind": "LimitRange",
            "metadata": {"name": "namespace-container-limits", "namespace": "default",
                         "labels": {"owner": "platform-team"},
                         "annotations": {"platform.example.com/policy":
                                         "Containers in this namespace may not exceed 128Mi (FINOPS-88)"}},
            "spec": {"limits": [{"type": "Container", "max": {"memory": "128Mi"}}]}}]},
    ]},
    "checks": [journey("ads"), {"type": "pods_ready", "selector": "opentelemetry.io/name=ad"},
               {"type": "pods_stable", "selector": "opentelemetry.io/name=ad", "min_age_s": 120}],
    "solution": ["kubectl delete limitrange namespace-container-limits",
                 "kubectl rollout undo deployment/ad",
                 "kubectl rollout status deployment/ad --timeout=300s"],
    "cause": "Two layers. ad's memory limit was cut to 48Mi, so the JVM is OOMKilled in a loop. Raising the "
             "limit to what ad needs is rejected at pod creation by LimitRange namespace-container-limits "
             "(max 128Mi), so the new ReplicaSet never gets pods and the old ones keep crashing.",
    "diagnose": [
        "ad pods: OOMKilled / CrashLoopBackOff; the memory limit is 48Mi.",
        "Raise the limit (e.g. back to the previous revision): `kubectl rollout status` stalls; the new "
        "ReplicaSet's events say 'forbidden: maximum memory usage per Container is 128Mi'.",
        "`kubectl get limitrange` shows namespace-container-limits.",
        "Raise or remove the LimitRange, then restore ad's memory settings.",
    ],
    "traps": ["Setting the limit to 128Mi to satisfy the LimitRange: the JVM still does not fit.",
              "Not reading ReplicaSet events, so the rejection stays invisible."],
    "drivers": ["sequential-layers", "fix-is-blocked", "silent-rejection"],
    "noise_desc": [],
    "pattern": "Guardrail (LimitRange/quota) blocking the remediation of an unrelated misconfiguration",
    "built_from": ["k8s-oom-cascade-001", "limitrange-rejects-048"],
    "validation": dict(VALIDATION),
})

# 111 ----------------------------------------------------------------------------
H.append({
    "id": "hard-flag-in-source-of-truth-111",
    "title": "Half of card payments are declined; a live fix does not survive the next restart",
    "mechanism": "hard/fault-in-source-config-live-fix-not-durable",
    "prompt": "About half of all card payments are being declined since this morning's configuration release. "
              "Find the cause and fix it.",
    "prompt_easier": "About half of card payments fail because a feature flag is on. Make sure the fix still holds "
                     "after the flag service restarts. Find the cause and fix it.",
    "fault": {"type": "flag_in_source_config", "flag": "paymentFailure", "variant": "50%"},
    "checks": [journey("checkout", repeat=8, max_avg_ms=5000)],
    "solution": ["python injectors/source_flag.py paymentFailure off"],
    "cause": "The feature flag paymentFailure is set to 50% in the flagd-config ConfigMap, the source flagd loads at "
             "startup. Flipping the flag only in flagd's live file (the Feature Flags UI / flagd-ui) fixes payments "
             "until flagd restarts, then the ConfigMap brings the failure back.",
    "diagnose": [
        "payment logs: about half of charges fail with the feature-flag-driven error.",
        "flagd's OFREP API (POST /ofrep/v1/evaluate/flags/paymentFailure) returns variant 50%.",
        "The live file in the flagd-ui container and the flagd-config ConfigMap both say 50%.",
        "Fix the ConfigMap (the source of truth) and restart flagd (or fix both the ConfigMap and the live file).",
    ],
    "traps": ["Fixing only the live flag file: passes now, fails after the verifier restarts flagd.",
              "Fixing only the ConfigMap without restarting flagd: nothing changes until the next restart."],
    "drivers": ["fix-must-be-durable", "intermittent", "two-sources-of-config"],
    "noise_desc": [],
    "pattern": "Live hotfix that is overwritten from the declarative source of truth on the next restart",
    "built_from": ["pay-fail-006 (flag)", "new mechanism flag_in_source_config"],
    "validation": dict(VALIDATION, restart_after_fix=["deployment/flagd"], restart_settle_s=45),
})

# 112 ----------------------------------------------------------------------------
H.append({
    "id": "hard-telemetry-noise-hides-scheduling-112",
    "title": "A loud telemetry outage hides the quiet scheduling failure that is actually hurting customers",
    "mechanism": "hard/loud-telemetry-outage-masks-scheduling-fault",
    "prompt": "International customers report that prices fail to load in their currency. At the same time, traces "
              "stopped arriving in Jaeger and the collector logs are full of export errors. Find what is breaking "
              "customers and fix it.",
    "prompt_easier": "Prices in foreign currencies fail to load because the currency service has no running pod. "
                     "The telemetry errors are a separate issue. Find the cause and fix it.",
    "fault": {"type": "composite", "steps": [
        {"type": "configmap_edit", "name": "otel-collector-agent", "key": "relay",
         "replace": [["endpoint: jaeger:4317", "endpoint: jaeger:4999"]],
         "restart_after": ["daemonset/otel-collector-agent"], "pause_s": 30},
        {"type": "object_patch", "kind": "node", "name": "ai-gym-worker", "namespace": None,
         "ops": [{"op": "append", "path": "/spec/taints",
                  "value": {"key": "dedicated", "value": "batch", "effect": "NoSchedule"}}]},
        {"type": "object_patch", "kind": "node", "name": "ai-gym-worker2", "namespace": None,
         "ops": [{"op": "append", "path": "/spec/taints",
                  "value": {"key": "dedicated", "value": "batch", "effect": "NoSchedule"}}],
         "recreate_pods_after": ["opentelemetry.io/name=currency"]},
    ]},
    "checks": [journey("currency"), {"type": "pods_ready", "selector": "opentelemetry.io/name=currency"}],
    "solution": ["kubectl taint nodes ai-gym-worker ai-gym-worker2 dedicated=batch:NoSchedule-",
                 "kubectl rollout status deployment/currency --timeout=300s"],
    "cause": "Both worker nodes carry a NoSchedule taint (dedicated=batch) and the currency pod, recreated "
             "afterwards, has no toleration, so it is Pending and currency conversion fails. Separately, the "
             "collector exports traces to the wrong Jaeger port: loud, real, but it does not affect customers.",
    "diagnose": [
        "The currency journey fails; `kubectl get pods -l opentelemetry.io/name=currency` shows Pending.",
        "`kubectl describe pod` (or events): 0/3 nodes available, untolerated taint dedicated=batch.",
        "`kubectl describe nodes` shows the taint on both workers.",
        "Remove the taints (or add a toleration); currency schedules and conversions work. The collector "
        "export errors can be fixed separately; they are not what customers see.",
    ],
    "traps": ["Spending the budget on the collector's export errors (real but not customer-facing).",
              "Restarting the currency pod (it stays Pending)."],
    "drivers": ["prioritization", "loud-secondary-fault", "red-herring"],
    "noise_desc": ["the trace pipeline is genuinely broken (wrong exporter port), with errors in collector logs"],
    "pattern": "Simultaneous incidents where the loudest one is not the one hurting customers",
    "built_from": ["otel-exporter-broken-085", "node-taint-046"],
    "validation": dict(VALIDATION),
})


# ------------------------------------------------------------------ writers
def spec_for(e, seed):
    return {
        "id": e["id"],
        "seed": seed,
        "stack": {"cluster": "kind-ai-gym", "apps": ["otel-demo"], "observability": ["prometheus", "grafana", "jaeger"]},
        "fault": e["fault"],
        "task": {"mode": "diagnose_and_mitigate", "prompt": e["prompt"]},
        "tools": ["kubectl", "curl"],
        "verifier": {"outcome": [f"{c['type']}:{c.get('journey') or c.get('selector') or ''}".rstrip(":")
                                 for c in e["checks"]],
                     "root_cause": [e["mechanism"].split("/", 1)[1]],
                     "forbidden": FORBIDDEN, "checks": e["checks"]},
        "solution": {"commands": e["solution"]},
        "validation": e["validation"],
        "budget": BUDGET,
        "meta": {"family": "hard", "tier": "hard", "mechanism": e["mechanism"], "title": e["title"],
                 "generated": "build_hard_scenarios.py", "est_pass_rate": None, "split": "hard",
                 "layers": 1 + sum(d in ("sequential-layers", "fix-reveals-next-fault", "fix-must-hold",
                                         "fix-must-be-durable", "fix-is-blocked", "hidden-second-actor")
                                   for d in e["drivers"]),
                 "difficulty_drivers": e["drivers"], "noise": e["noise_desc"],
                 "realistic_pattern": e["pattern"], "built_from": e["built_from"],
                 "prompt_easier": e["prompt_easier"]},
    }


def reference_for(e):
    lines = [f"# Reference solution: {e['id']}", "", f"**{e['title']}**", "",
             f"**Root cause:** {e['cause']}", "", "## How a careful SRE finds it", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(e["diagnose"], 1)]
    lines += ["", "## Traps (why this is hard)", ""] + [f"- {t}" for t in e["traps"]]
    if e["noise_desc"]:
        lines += ["", "## Noise in this scenario (not the cause)", ""] + [f"- {n}" for n in e["noise_desc"]]
    lines += ["", "## Fix", "", "```bash", *e["solution"], "```", "", "## Confirm", "",
              f"`python verifiers/verify.py scenarios/{e['id']}` passes.", ""]
    return "\n".join(lines)


def main():
    ids = [e["id"] for e in H]
    assert len(ids) == len(set(ids)), "duplicate ids"
    mechs = [e["mechanism"] for e in H]
    assert len(mechs) == len(set(mechs)), "duplicate mechanisms"
    for e in H:
        d = SCEN / e["id"]
        d.mkdir(parents=True, exist_ok=True)
        seed = 1000 + int(e["id"].rsplit("-", 1)[1])
        (d / "spec.yaml").write_text(yaml.dump(spec_for(e, seed), Dumper=Dumper, sort_keys=False, width=110,
                                               allow_unicode=True))
        (d / "reference_solution.md").write_text(reference_for(e))
    print(f"wrote {len(H)} Hard scenarios")


if __name__ == "__main__":
    sys.exit(main())
