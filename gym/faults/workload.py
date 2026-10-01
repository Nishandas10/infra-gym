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


@mechanism("workload_patch", "workload",
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


@mechanism("memory_limit_misconfig", "resource-limits",
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
