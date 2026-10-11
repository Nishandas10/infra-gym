"""Infrastructure-level faults driven by Chaos Mesh custom resources.

The scenario folder holds the Chaos Mesh YAML (as in Playbook step 3.3). Chaos
Mesh's own controller is the injector; deleting the object removes the fault.
"""
from __future__ import annotations

import time

import yaml

from .. import kube
from . import mechanism


def load_manifests(fault, ctx):
    if "manifest" in fault and isinstance(fault["manifest"], (dict, list)):
        docs = fault["manifest"] if isinstance(fault["manifest"], list) else [fault["manifest"]]
    else:
        path = ctx.scenario_dir / fault.get("manifest", "chaos.yaml")
        docs = [d for d in yaml.safe_load_all(path.read_text()) if d]
    return docs


def _resource(doc):
    return f"{doc['kind'].lower()}.chaos-mesh.org"


def wait_injected(doc, timeout=90):
    """Wait until Chaos Mesh reports the fault as injected (Schedules just need to exist)."""
    if doc["kind"] == "Schedule":
        return True
    ns = doc["metadata"].get("namespace", kube.APP_NS)

    def injected():
        obj = kube.get(_resource(doc), doc["metadata"]["name"], namespace=ns, missing_ok=True) or {}
        conds = {c["type"]: c["status"] for c in obj.get("status", {}).get("conditions", []) or []}
        return conds.get("AllInjected") == "True"
    return kube.wait_until(injected, timeout=timeout, interval=3)


@mechanism("chaos.mesh", "chaos", "Apply Chaos Mesh experiment(s) from the scenario folder")
def chaos_mesh(fault, undo, ctx):
    docs = load_manifests(fault, ctx)
    for doc in docs:
        ns = doc["metadata"].setdefault("namespace", kube.APP_NS)
        undo.created(_resource(doc), doc["metadata"]["name"], namespace=ns)
        kube.apply(doc, namespace=ns)
    for doc in docs:
        if not wait_injected(doc):
            raise RuntimeError(f"Chaos Mesh did not report {doc['kind']}/{doc['metadata']['name']} as injected")
    # Optional: replace some pods afterwards (an ordinary reschedule), e.g. so that
    # clients must re-resolve a name while DNS is broken. Their replicasets
    # recreate them, so there is nothing to undo.
    for selector in fault.get("kill_pods_after", []):
        time.sleep(3)
        kube.kubectl("delete", "pod", "-l", selector, "--wait=false")
    time.sleep(2)
