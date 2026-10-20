"""bench/world.py clear_history, offline: what an earlier episode leaves for the next agent to read is deleted before
each episode; what the shop runs on, and the good revision a `rollout undo` fix goes back to, are kept."""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import world  # noqa: E402


def dep(name, rev):
    return {"metadata": {"name": name, "annotations": {world.REVISION: str(rev)}}}


def rs(name, owner, rev, replicas=0, live=0):
    return {"metadata": {"name": name, "annotations": {world.REVISION: str(rev)},
                         "ownerReferences": [{"kind": "Deployment", "name": owner}]},
            "spec": {"replicas": replicas}, "status": {"replicas": live}}


def cr(name, owner_uid, rev):
    return {"metadata": {"name": name, "ownerReferences": [{"uid": owner_uid}]}, "revision": rev}


def test_clear_history(monkeypatch):
    objects = {
        ("deployments.apps", "default"): [dep("cart", 7), dep("ad", 2)],
        ("replicasets.apps", "default"): [
            rs("cart-7", "cart", 7, replicas=1, live=1),     # current: kept
            rs("cart-6", "cart", 6),                         # a past episode's revision: deleted
            rs("cart-5", "cart", 5),                         # deleted
            rs("ad-1", "ad", 1, replicas=0, live=1),          # old but still has a pod (rollout in progress): kept
            rs("ad-2", "ad", 2, replicas=1, live=1),
            {**rs("orphan-1", "gone", 1)},                   # owner not a current Deployment: left alone
        ],
        ("controllerrevisions.apps", "default"): [cr("agent-5", "u1", 5), cr("agent-4", "u1", 4), cr("x-1", "u2", 1)],
    }
    deleted = []
    monkeypatch.setattr(world.kube, "items", lambda kind, namespace=None: objects.get((kind, namespace), []))
    monkeypatch.setattr(world.kube, "kubectl", lambda *a, namespace=None, **kw: deleted.append((namespace, a)))
    out = world.clear_history(namespaces=("default",))
    assert out == {"replicasets": 2, "controllerrevisions": 1}
    assert ("default", ("delete", "replicasets.apps", "cart-6", "cart-5", "--wait=false", "--ignore-not-found")) in deleted
    assert ("default", ("delete", "controllerrevisions.apps", "agent-4", "--wait=false", "--ignore-not-found")) in deleted
    assert ("default", ("delete", "events", "--all", "--wait=false")) in deleted


def test_nothing_to_delete_still_clears_events(monkeypatch):
    calls = []
    monkeypatch.setattr(world.kube, "items", lambda kind, namespace=None: [])
    monkeypatch.setattr(world.kube, "kubectl", lambda *a, namespace=None, **kw: calls.append((namespace, a[:2])))
    assert world.clear_history() == {"replicasets": 0, "controllerrevisions": 0}
    assert calls == [(ns, ("delete", "events")) for ns in world.HISTORY_NAMESPACES]
