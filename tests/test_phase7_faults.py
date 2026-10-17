"""Phase 7 fault mechanisms and checks, offline: k8s.bad_rollout, k8s.separate_pods, reachable_from_nodes.

test_inject_revert.py already injects and reverts every scenario exactly; these tests check what each new
mechanism does in between, and the parts the fake cluster cannot show on its own (ReplicaSet pruning, the
per-node probe check).
"""
from __future__ import annotations

from types import SimpleNamespace as NS

from gym import checks, faults, kube, toolbox
from gym import undo as undo_mod
from gym.spec import all_specs, load
from tests.fakes import FakeCluster, install

SPECS = {p.parent.name: p for p in all_specs()}
CAUSE = "kubernetes.io/change-cause"


def env(fake, deployment):
    c = fake.obj("deployment", deployment)["spec"]["template"]["spec"]["containers"][0]
    return {e["name"]: e.get("value") for e in c["env"]}


def test_bad_rollout_two_releases(monkeypatch, tmp_path):
    fake = FakeCluster()
    install(fake, monkeypatch, tmp_path)
    spec, sdir = load(SPECS["rollout-two-bad-releases-114"])
    faults.inject(spec, sdir)
    dep = fake.obj("deployment", "shipping")
    assert env(fake, "shipping")["QUOTE_ADDR"] == "http://quote:8081"
    assert env(fake, "shipping")["OTEL_EXPORTER_OTLP_ENDPOINT"].endswith(":4999")
    assert dep["metadata"]["annotations"][CAUSE].startswith("shipping 3.1.2")
    assert dep["spec"]["template"]["metadata"]["labels"]["app.kubernetes.io/version"] == "3.1.2"
    assert not faults.revert(spec)
    dep = fake.obj("deployment", "shipping")
    assert CAUSE not in dep["metadata"]["annotations"]
    assert env(fake, "shipping")["QUOTE_ADDR"] == "http://quote:8080"


def replicaset(name, revision, owner="shipping"):
    return {"apiVersion": "apps/v1", "kind": "ReplicaSet",
            "metadata": {"name": name, "namespace": kube.APP_NS,
                         "annotations": {"deployment.kubernetes.io/revision": str(revision)},
                         "ownerReferences": [{"kind": "Deployment", "name": owner}]}}


def test_prune_keeps_old_and_current_revisions(monkeypatch, tmp_path):
    fake = FakeCluster()
    install(fake, monkeypatch, tmp_path)
    for rs in (replicaset("shipping-a", 3), replicaset("shipping-b", 4), replicaset("shipping-c", 5),
               replicaset("quote-x", 9, owner="quote")):
        fake.apply(rs)
    dep = fake.obj("deployment", "shipping")
    dep["metadata"]["annotations"]["deployment.kubernetes.io/revision"] = "5"
    undo_mod.run_hook({"prune_replicasets": {"deployment": "shipping", "ns": kube.APP_NS, "keep": ["shipping-a"]}})
    left = {rs["metadata"]["name"] for rs in fake.items("replicaset")}
    # shipping-a existed before the fault, shipping-c is what the Deployment runs now, quote-x is not shipping's
    assert left == {"shipping-a", "shipping-c", "quote-x"}


def test_bad_rollout_records_existing_replicasets(monkeypatch, tmp_path):
    fake = FakeCluster()
    install(fake, monkeypatch, tmp_path)
    fake.apply(replicaset("payment-old", 1, owner="payment"))
    spec, sdir = load(SPECS["rollout-wrong-artifact-115"])
    faults.inject(spec, sdir)
    hooks = [a["hook"]["prune_replicasets"] for a in undo_mod.UndoLog(spec["id"]).actions if a["op"] == "hook"]
    assert hooks == [{"deployment": "payment", "ns": kube.APP_NS, "keep": ["payment-old"]}]
    image = fake.obj("deployment", "payment")["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image.endswith("-quote")
    assert not faults.revert(spec)


def place(fake, selector, node):
    for p in fake.items("pod", selector=selector):
        fake.obj("pod", p["metadata"]["name"])["spec"]["nodeName"] = node


def test_separate_pods_moves_callers_off_the_target_node(monkeypatch, tmp_path):
    fake = FakeCluster()
    install(fake, monkeypatch, tmp_path)
    node, other = fake.workers()
    for sel in ("opentelemetry.io/name=currency", "opentelemetry.io/name=frontend", "opentelemetry.io/name=checkout"):
        place(fake, sel, node)
    spec, sdir = load(SPECS["svc-internal-traffic-local-113"])
    faults.inject(spec, sdir)
    assert fake.obj("service", "currency")["spec"]["internalTrafficPolicy"] == "Local"
    assert fake.node_of("opentelemetry.io/name=currency") == {node}
    assert fake.node_of("opentelemetry.io/name=frontend") == {other}
    assert fake.node_of("opentelemetry.io/name=checkout") == {other}
    assert not fake.obj("node", node)["spec"].get("unschedulable"), "the node must be uncordoned again"
    assert not faults.revert(spec)
    assert fake.obj("service", "currency")["spec"]["internalTrafficPolicy"] == "Cluster"


def test_separate_pods_leaves_pods_alone_when_already_apart(monkeypatch, tmp_path):
    fake = FakeCluster()
    install(fake, monkeypatch, tmp_path)
    node, other = fake.workers()
    place(fake, "opentelemetry.io/name=currency", node)
    place(fake, "opentelemetry.io/name=frontend", other)
    place(fake, "opentelemetry.io/name=checkout", other)
    spec, sdir = load(SPECS["svc-internal-traffic-local-113"])
    faults.inject(spec, sdir)
    assert not fake.pod_deletions
    assert not [a for a in undo_mod.UndoLog(spec["id"]).actions if a.get("kind") == "node"]
    assert not faults.revert(spec)


def test_reachable_from_nodes(monkeypatch):
    answers = {}
    monkeypatch.setattr(kube, "worker_nodes", lambda: ["w1", "w2"])
    monkeypatch.setattr(toolbox, "node_probes", lambda: {"w1": "probe-1", "w2": "probe-2"})
    monkeypatch.setattr(kube, "exec_in", lambda pod, cmd, **_: NS(stdout=answers[pod] + "\n", stderr="", returncode=0))
    answers.update({"probe-1": "OPEN", "probe-2": "OPEN"})
    assert checks.c_reachable_from_nodes("currency", 8080)[0] == checks.PASS
    answers["probe-2"] = "BLOCKED"
    status, msg = checks.c_reachable_from_nodes("currency", 8080)
    assert status == checks.FAIL and "w2" in msg and "w1" not in msg.split("(")[0]
    answers["probe-2"] = "Error from server (NotFound)"
    assert checks.c_reachable_from_nodes("currency", 8080)[0] == checks.UNKNOWN
    monkeypatch.setattr(toolbox, "node_probes", lambda: {"w1": "probe-1"})
    assert checks.c_reachable_from_nodes("currency", 8080)[0] == checks.UNKNOWN
