"""Every scenario: inject, then revert, against the fake cluster (tests/fakes.py).

Checks for each scenario that
  * injection runs against the real object shapes (no missing objects, env vars or containers),
  * it changes something observable (objects, flagd's live flags, or commands run in pods),
  * revert reports no errors and restores every object and flag exactly,
  * every undo command of an exec fault is run on revert.
The Hard scenarios also get a specific check of the state right after injection.
"""
from __future__ import annotations

import json

import pytest

from gym import faults
from gym.spec import all_specs, load
from tests.fakes import FakeCluster, install

SPECS = all_specs()


def env_of(fake, deployment):
    return fake.obj("deployment", deployment)["spec"]["template"]["spec"]["containers"][0]["env"]


def container(fake, deployment):
    return fake.obj("deployment", deployment)["spec"]["template"]["spec"]["containers"][0]


EXPECT = {   # what must be true right after injection (Hard tier)
    "hard-fix-reverted-by-cronjob-101": lambda f: (
        {"name": "PAYMENT_PORT", "value": "8081"} in env_of(f, "payment")
        and f.obj("cronjob", "payment-config-sync") and f.obj("role", "config-sync")),
    "hard-egress-policy-blocks-db-102": lambda f: (
        f.obj("networkpolicy", "product-catalog-egress-hardening") and f.obj("job", "astronomy-db-backup-nightly")),
    "hard-cart-chained-addr-auth-103": lambda f: (
        {"name": "VALKEY_ADDR", "value": "valkey-cart:6380"} in env_of(f, "cart")
        and any("requirepass" in c for _, c, _ in f.execs) and f.obj("secret", "valkey-cart-credentials")),
    "hard-ghost-legacy-email-pods-104": lambda f: f.obj("deployment", "email-v1-legacy"),
    "hard-silent-ledger-write-denied-105": lambda f: any("REVOKE INSERT" in " ".join(c) for _, c, _ in f.execs),
    "hard-allowlist-forgets-checkout-106": lambda f: (
        f.obj("networkpolicy", "product-catalog-allow-clients")
        and f.obj("deployment", "payment")["metadata"]["annotations"].get("kubernetes.io/change-cause")),
    "hard-masked-second-fault-107": lambda f: (
        f.obj("service", "shipping")["spec"]["ports"][0]["targetPort"] == 8888
        and {"name": "PRODUCT_CATALOG_ADDR", "value": "product-catalog:9090"} in env_of(f, "checkout")),
    "hard-pinned-endpoints-108": lambda f: (
        "selector" not in f.obj("service", "quote")["spec"]
        and f.obj("endpointslice", "quote-pinned")["endpoints"][0]["addresses"] == ["10.244.250.17"]),
    "hard-duplicate-env-override-109": lambda f: (
        [e["value"] for e in env_of(f, "recommendation") if e["name"] == "PRODUCT_CATALOG_ADDR"][-1]
        == "product-catalog:3550"
        and container(f, "recommendation").get("envFrom")),
    "hard-oom-fix-blocked-by-limitrange-110": lambda f: (
        container(f, "ad")["resources"]["limits"]["memory"] == "48Mi"
        and f.obj("limitrange", "namespace-container-limits")),
    "hard-flag-in-source-of-truth-111": lambda f: (
        f.flags_source()["paymentFailure"]["defaultVariant"] == "50%"
        and f.flags_live()["paymentFailure"]["defaultVariant"] == "50%"),
    "hard-telemetry-noise-hides-scheduling-112": lambda f: (
        "jaeger:4999" in f.obj("configmap", "otel-collector-agent")["data"]["relay"]
        and all(any(t["key"] == "dedicated" for t in f.obj("node", n)["spec"].get("taints", []))
                for n in ("ai-gym-worker", "ai-gym-worker2"))),
    "hard-job-sidecar-never-completes-127": lambda f: (
        [c["name"] for c in f.obj("job", "ledger-migrate-7")["spec"]["template"]["spec"]["containers"]]
        == ["migrate", "log-shipper"]
        and f.obj("rolebinding", "job-status-reader")
        and f.obj("deployment", "accounting")["spec"]["strategy"] == {"type": "Recreate"}
        and [c["name"] for c in f.obj("deployment", "accounting")["spec"]["template"]["spec"]["initContainers"]]
        == ["wait-for-kafka", "wait-for-ledger-migration"]),
}


# Injections that end where they started (a scale to zero and back); tests/test_false_alarm.py checks the state in
# between.
NO_NET_CHANGE = {"fa-drained-consumer-lag-118"}


def test_every_hard_scenario_has_an_expectation():
    hard = {p.parent.name for p in SPECS if p.parent.name.startswith("hard-")}
    assert hard == set(EXPECT)


@pytest.mark.parametrize("spec_path", SPECS, ids=[p.parent.name for p in SPECS])
def test_inject_then_revert_exactly(spec_path, monkeypatch, tmp_path):
    fake = FakeCluster()
    install(fake, monkeypatch, tmp_path)
    spec, sdir = load(spec_path)
    objects_before, flags_before = fake.state(), fake.flags_live()

    faults.inject(spec, sdir)

    changed = (fake.state() != objects_before or fake.flags_live() != flags_before
               or any(cmd[:1] != ["cat"] for _, cmd, _ in fake.execs) or fake.kubelet_stopped)
    assert changed or spec["id"] in NO_NET_CHANGE, "injection changed nothing"
    if spec["id"] in EXPECT:
        assert EXPECT[spec["id"]](fake), "injected state is not as expected"

    execs_at_revert = len(fake.execs)
    errors = faults.revert(spec)
    assert not errors, f"revert errors: {errors}"

    after = fake.state()
    diff = sorted(str(k) for k in set(objects_before) | set(after) if objects_before.get(k) != after.get(k))
    assert not diff, f"not restored exactly: {diff}"
    assert fake.flags_live() == flags_before, "flagd's live flags not restored"
    assert not fake.kubelet_stopped, f"kubelet still stopped on {sorted(fake.kubelet_stopped)}"

    reverted_cmds = [cmd for _, cmd, _ in fake.execs[execs_at_revert:]]
    for st in spec["fault"]["steps"]:
        for cmd in st.get("undo_commands", []):
            assert cmd in reverted_cmds, f"undo command not run: {json.dumps(cmd)[:120]}"


def test_workers_placeholder_patches_every_worker_and_only_workers(monkeypatch, tmp_path):
    fake = FakeCluster()
    install(fake, monkeypatch, tmp_path)
    spec, sdir = load(next(p for p in SPECS if p.parent.name == "node-cordoned-045"))
    faults.inject(spec, sdir)
    nodes = {n["metadata"]["name"]: n for n in fake.items("node", namespace=None)}
    workers = {name for name, n in nodes.items() if "node-role.kubernetes.io/control-plane" not in n["metadata"]["labels"]}
    assert workers and len(workers) < len(nodes)
    for name, n in nodes.items():
        assert bool(n["spec"].get("unschedulable")) == (name in workers), name
    assert not faults.revert(spec)
    assert not any(n["spec"].get("unschedulable") for n in fake.items("node", namespace=None))
