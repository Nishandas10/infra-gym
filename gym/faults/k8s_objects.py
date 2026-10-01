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


@mechanism("object_patch", "k8s-object", "Patch any object (JSON patch), restoring the touched fields on revert")
def object_patch(fault, undo, ctx):
    ns = _ns(fault)
    kind, name = fault["kind"], fault["name"]
    # Restarts recorded first run last on revert: restore the config, then restart its readers.
    for target in fault.get("restart_after", []):
        undo.on_revert_restart(target, ns)
    live = kube.get(kind, name, namespace=ns)
    ops = expand(live, fault["ops"])
    undo.snapshot(kind, name, fault.get("snapshot") or _default_snapshot(ops), namespace=ns)
    kube.patch(kind, name, ops, "json", namespace=ns)
    _after(fault, undo, ns)


@mechanism("configmap_edit", "k8s-object",
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


@mechanism("create_objects", "k8s-object", "Create objects (policies, quotas, webhooks, rogue workloads...)")
def create_objects(fault, undo, ctx):
    for doc in _manifests(fault, ctx):
        ns = doc.get("metadata", {}).get("namespace", _ns(fault))
        undo.created(doc["kind"], doc["metadata"]["name"], namespace=ns)
        kube.apply(doc, namespace=ns)
    _after(fault, undo, _ns(fault))


@mechanism("delete_object", "k8s-object", "Delete an object; revert recreates it from its snapshot")
def delete_object(fault, undo, ctx):
    ns = _ns(fault)
    obj = kube.get(fault["kind"], fault["name"], namespace=ns)
    undo.deleted(obj, namespace=ns)
    kube.delete(fault["kind"], fault["name"], namespace=ns, wait=True)
    _after(fault, undo, ns)
