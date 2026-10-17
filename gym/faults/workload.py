"""Faults in a workload's own spec (Deployment / StatefulSet / DaemonSet)."""
from __future__ import annotations

from .. import kube
from . import mechanism
from .ops import expand


def first_container(obj):
    return obj["spec"]["template"]["spec"]["containers"][0]["name"]


def snapshot_workload(undo, kind, name, namespace=kube.APP_NS):
    """Record template, replicas, paused flag and rollout strategy, so revert restores them exactly."""
    pointers = ["/spec/template", "/spec/replicas", "/spec/paused"]
    pointers.append("/spec/updateStrategy" if kind.lower().startswith(("daemonset", "statefulset")) else "/spec/strategy")
    return undo.snapshot(kind, name, pointers, namespace=namespace)


def selector_of(obj):
    labels = obj["spec"]["selector"].get("matchLabels", {})
    return ",".join(f"{k}={v}" for k, v in labels.items())


def recreate_pods(obj, namespace=kube.APP_NS):
    """Delete the current pods so replacements are built from the (now broken) template."""
    kube.kubectl("delete", "pod", "-l", selector_of(obj), "--wait=false", namespace=namespace)


@mechanism("k8s.workload_patch", "workload",
           "Patch a workload (pod template, replicas, paused...) and optionally replace its pods")
def workload_patch(fault, undo, ctx):
    kind = fault.get("kind", "deployment")
    ns = fault.get("namespace", kube.APP_NS)
    obj = snapshot_workload(undo, kind, fault["target"], namespace=ns)
    ops = expand(obj, fault["ops"], fault.get("container"))
    if fault.get("strategy") == "Recreate":
        # With the default RollingUpdate a new pod that cannot start leaves the old
        # pod serving, so there is no outage. Recreate (common for single-replica
        # services) removes the old pod first.
        ops.insert(0, {"op": "replace" if obj["spec"].get("strategy") else "add",
                       "path": "/spec/strategy", "value": {"type": "Recreate"}})
    kube.patch(kind, fault["target"], ops, "json", namespace=ns)
    if fault.get("recreate_pods", True) and fault.get("strategy") != "Recreate":
        recreate_pods(obj, namespace=ns)


@mechanism("k8s.memory_limit", "resource-limits",
           "Memory request/limit set far below what the service needs -> OOMKilled / CrashLoopBackOff")
def memory_limit_misconfig(fault, undo, ctx):
    name = fault["target_deployment"]
    obj = snapshot_workload(undo, "deployment", name)
    container = fault.get("container") or first_container(obj)
    resources = {"limits": {"memory": fault["bad_memory_limit"]}}
    if fault.get("bad_memory_request"):
        resources["requests"] = {"memory": fault["bad_memory_request"]}
    body = {"spec": {"template": {"spec": {"containers": [{"name": container, "resources": resources}]}}}}
    if fault.get("strategy") == "Recreate":
        body["spec"]["strategy"] = {"type": "Recreate", "rollingUpdate": None}
    kube.patch("deployment", name, body)
    if fault.get("strategy") != "Recreate":
        kube.kubectl("delete", "pod", "-l", fault["target_label"], "--wait=false")


CHANGE_CAUSE = "kubernetes.io/change-cause"


def owned_replicasets(deployment, namespace=kube.APP_NS):
    return [rs for rs in kube.items("replicasets", namespace=namespace)
            if any(o.get("kind") == "Deployment" and o.get("name") == deployment
                   for o in rs["metadata"].get("ownerReferences") or [])]


@mechanism("k8s.bad_rollout", "rollout",
           "Roll a bad change out as a new Deployment revision, with a change-cause, as a CI deploy would")
def bad_rollout(fault, undo, ctx):
    """Unlike k8s.workload_patch, every step leaves its own revision in `kubectl rollout history` (it waits for
    the rollout when wait_s is set, so two steps in a row stay two revisions), which makes `kubectl rollout undo`
    a valid fix. The ReplicaSets it creates are deleted on revert, so no episode sees an earlier one's history."""
    name, ns = fault["target"], fault.get("namespace", kube.APP_NS)
    # Recorded first, so it runs last on revert: after the template is restored, the revisions this step
    # created hold no pods the Deployment needs.
    keep = [rs["metadata"]["name"] for rs in owned_replicasets(name, ns)]
    undo.add({"op": "hook", "hook": {"prune_replicasets": {"deployment": name, "ns": ns, "keep": keep}}})
    obj = snapshot_workload(undo, "deployment", name, namespace=ns)
    cause = "/metadata/annotations/" + kube.escape(CHANGE_CAUSE)
    undo.snapshot("deployment", name, [cause], namespace=ns)
    ops = expand(obj, fault["ops"], fault.get("container"))
    if not obj["metadata"].get("annotations"):
        ops.append({"op": "add", "path": "/metadata/annotations", "value": {}})
    ops.append({"op": "add", "path": cause, "value": fault["change_cause"]})
    kube.patch("deployment", name, ops, "json", namespace=ns)
    if fault.get("wait_s"):
        kube.kubectl("rollout", "status", f"deployment/{name}", f"--timeout={fault['wait_s']}s", namespace=ns,
                     timeout=fault["wait_s"] + 30)


def _running(selector, namespace):
    return [p for p in kube.pods(selector, namespace=namespace) if not p["metadata"].get("deletionTimestamp")
            and p.get("status", {}).get("phase") not in ("Succeeded", "Failed")]


@mechanism("k8s.separate_pods", "placement",
           "Move the pods of `away_from` off the node that runs `target`'s pod (cordon, recreate, uncordon)")
def separate_pods(fault, undo, ctx):
    """Makes a node-dependent fault observable on every run: with single replicas, the scheduler would otherwise
    put the callers on the target's node in some runs and hide the fault. Changes no object for good; the node is
    uncordoned before it returns (and on revert, should the injection stop half-way)."""
    ns = fault.get("namespace", kube.APP_NS)
    nodes = {p["spec"].get("nodeName") for p in _running(fault["target"], ns)}
    if len(nodes) != 1 or None in nodes:
        raise kube.KubeError(f"{fault['target']}: expected running pods on exactly one node, found {sorted(map(str, nodes))}")
    node = nodes.pop()
    movers = [sel for sel in fault["away_from"]
              if any(p["spec"].get("nodeName") == node for p in _running(sel, ns))]
    if not movers:
        return
    undo.snapshot("node", node, ["/spec/unschedulable"], namespace=None)
    kube.patch("node", node, {"spec": {"unschedulable": True}}, "merge", namespace=None)
    try:
        for sel in movers:
            kube.kubectl("delete", "pod", "-l", sel, "--wait=false", namespace=ns)

        def moved():
            for sel in movers:
                pods = _running(sel, ns)
                if not pods or any(not kube.pod_ready(p) or p["spec"].get("nodeName") == node for p in pods):
                    return False
            return True
        if not kube.wait_until(moved, fault.get("timeout_s", 240)):
            raise kube.KubeError(f"pods of {', '.join(movers)} did not become ready away from node {node}")
    finally:
        kube.patch("node", node, {"spec": {"unschedulable": None}}, "merge", namespace=None)
