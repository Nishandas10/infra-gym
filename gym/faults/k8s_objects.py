"""Faults made by changing, creating or deleting Kubernetes objects
(Services, ConfigMaps, Nodes, Namespaces, NetworkPolicies, quotas, webhooks...)."""
from __future__ import annotations

import time

import yaml

from .. import kube
from ..undo import restart
from . import mechanism
from .ops import expand


def _ns(fault):
    # cluster-scoped kinds (nodes, namespaces, webhooks...) pass namespace: null
    return fault["namespace"] if "namespace" in fault else kube.APP_NS


def _default_snapshot(ops):
    """Snapshot the first two levels of every patched path (e.g. /spec/selector, /data/Corefile)."""
    pointers = set()
    for op in ops:
        toks = op["path"].strip("/").split("/")
        pointers.add("/" + "/".join(toks[:2]))
    return sorted(pointers)


def _after(fault, undo, namespace):
    if fault.get("restart_after"):
        # Give the kubelet time to see the new ConfigMap; pods restarted within a second of
        # the edit can still be handed the cached old version (seen with the collector).
        time.sleep(fault.get("restart_delay_s", 15))
    for target in fault.get("restart_after", []):
        restart(target, namespace)
    for selector in fault.get("recreate_pods_after", []):
        time.sleep(fault.get("settle_s", 3))
        kube.kubectl("delete", "pod", "-l", selector, "--wait=false", namespace=kube.APP_NS)


WORKERS = "$workers"   # name placeholder: every worker node (worlds/*.yaml worker_selector)
WORKER = "$worker"     # name placeholder: one worker node, the first by name (the same one on every run)


def node_names(name):
    """The objects a step named: every worker for $workers, the first worker for $worker, else just `name`."""
    if name == WORKERS:
        return kube.worker_nodes()
    if name == WORKER:
        return sorted(kube.worker_nodes())[:1]
    return [name]


@mechanism("k8s.object_patch", "k8s-object",
           "Patch any object (JSON patch), restoring the touched fields on revert; "
           "name: $workers patches every worker node, $worker the first one by name")
def object_patch(fault, undo, ctx):
    ns = _ns(fault)
    kind = fault["kind"]
    names = node_names(fault["name"])
    # Restarts recorded first run last on revert: restore the config, then restart its readers.
    for target in fault.get("restart_after", []):
        undo.on_revert_restart(target, ns)
    for name in names:
        live = kube.get(kind, name, namespace=ns)
        ops = expand(live, fault["ops"])
        undo.snapshot(kind, name, fault.get("snapshot") or _default_snapshot(ops), namespace=ns)
        kube.patch(kind, name, ops, "json", namespace=ns)
    _after(fault, undo, ns)


@mechanism("k8s.configmap_edit", "k8s-object",
           "Edit text inside a ConfigMap key (CoreDNS Corefile, collector config...) and restart its readers")
def configmap_edit(fault, undo, ctx):
    ns = _ns(fault)
    name, key = fault["name"], fault["key"]
    for target in fault.get("restart_after", []):
        undo.on_revert_restart(target, ns)
    obj = undo.snapshot("configmap", name, [f"/data/{kube.escape(key)}"], namespace=ns)
    text = obj["data"][key]
    for old, new in fault["replace"]:
        if old not in text:
            raise ValueError(f"configmap {name}/{key}: text {old!r} not found")
        text = text.replace(old, new, 1)
    kube.patch("configmap", name, {"data": {key: text}}, "merge", namespace=ns)
    _after(fault, undo, ns)


def _manifests(fault, ctx):
    if "manifests" in fault:
        return fault["manifests"]
    path = ctx.scenario_dir / fault.get("manifest_file", "objects.yaml")
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


@mechanism("k8s.create_objects", "k8s-object", "Create objects (policies, quotas, webhooks, rogue workloads...)")
def create_objects(fault, undo, ctx):
    for doc in _manifests(fault, ctx):
        ns = doc.get("metadata", {}).get("namespace", _ns(fault))
        undo.created(doc["kind"], doc["metadata"]["name"], namespace=ns)
        kube.apply(doc, namespace=ns)
    _after(fault, undo, _ns(fault))


@mechanism("k8s.delete_object", "k8s-object", "Delete an object; revert recreates it from its snapshot")
def delete_object(fault, undo, ctx):
    ns = _ns(fault)
    obj = kube.get(fault["kind"], fault["name"], namespace=ns)
    undo.deleted(obj, namespace=ns)
    kube.delete(fault["kind"], fault["name"], namespace=ns, wait=True)
    _after(fault, undo, ns)


def _numeric_target_ports(svc, namespace):
    """Service ports with targetPort resolved to a number (named ports via a backing pod)."""
    selector = ",".join(f"{k}={v}" for k, v in (svc["spec"].get("selector") or {}).items())
    pod = None
    out = []
    for p in svc["spec"]["ports"]:
        target = p.get("targetPort", p["port"])
        if isinstance(target, str) and not target.isdigit():
            if pod is None:
                pods = kube.items("pods", namespace=namespace, selector=selector) if selector else []
                if not pods:
                    raise ValueError(f"service {svc['metadata']['name']}: named targetPort {target!r} "
                                     "and no pod to resolve it from")
                pod = pods[0]
            target = next(cp["containerPort"] for c in pod["spec"]["containers"]
                          for cp in c.get("ports", []) if cp.get("name") == target)
        entry = {"port": int(target), "protocol": p.get("protocol", "TCP")}
        if p.get("name"):
            entry["name"] = p["name"]
        out.append(entry)
    return out


@mechanism("k8s.pin_endpoints", "k8s-object",
           "Make a Service selector-less and point it at fixed IPs with a hand-made EndpointSlice "
           "(the classic 'pinned during an incident, never unpinned')")
def pin_endpoints(fault, undo, ctx):
    ns = _ns(fault)
    name = fault["service"]
    svc = kube.get("service", name, namespace=ns)
    ports = _numeric_target_ports(svc, ns)
    slice_name = fault.get("slice_name", f"{name}-pinned")
    manifest = {
        "apiVersion": "discovery.k8s.io/v1", "kind": "EndpointSlice",
        "metadata": {"name": slice_name, "namespace": ns,
                     "labels": {"kubernetes.io/service-name": name,
                                "endpointslice.kubernetes.io/managed-by": fault.get("managed_by", "ops-manual")},
                     "annotations": fault.get("annotations", {})},
        "addressType": "IPv4",
        "ports": ports,
        "endpoints": [{"addresses": [ip], "conditions": {"ready": True}} for ip in fault["ips"]],
    }
    # Undo runs newest first: put the selector back (the controller recreates its own
    # slices), then delete the hand-made slice.
    undo.created("endpointslices.discovery.k8s.io", slice_name, namespace=ns)
    kube.apply(manifest, namespace=ns)
    undo.snapshot("service", name, ["/spec/selector"], namespace=ns)
    kube.patch("service", name, [{"op": "remove", "path": "/spec/selector"}], "json", namespace=ns)
    if fault.get("clear_stale"):
        _clear_controller_endpoints(name, ns)
    _after(fault, undo, ns)


CONTROLLER_SLICES = ("endpointslice-controller.k8s.io", "endpointslicemirroring-controller.k8s.io")


def _clear_controller_endpoints(name, ns):
    """Without a selector, Kubernetes leaves the Service's old Endpoints object and EndpointSlice in place, and
    the mirroring controller copies those Endpoints (still listing the real pods) into a new slice: the pinned IP
    then gets only part of the traffic. Delete them, the Endpoints first so nothing is mirrored again. No undo is
    needed: once the selector is back, the controllers recreate both."""
    kube.delete("endpoints", name, namespace=ns)
    for _ in range(2):   # a slice mirrored just before the Endpoints went away is caught the second time
        for s in kube.items("endpointslices", namespace=ns, selector=f"kubernetes.io/service-name={name}"):
            if s["metadata"].get("labels", {}).get("endpointslice.kubernetes.io/managed-by") in CONTROLLER_SLICES:
                kube.delete("endpointslices", s["metadata"]["name"], namespace=ns)
        time.sleep(3)
