"""Snapshot everything an AI agent could change, and put it back exactly after an episode.

The gym's undo log reverts the injected fault. But an agent can change other things too
(edit a deployment, label a node, add a NetworkPolicy). Without this, one episode's
leftovers would leak into the next one and corrupt the benchmark.
"""
from __future__ import annotations

import copy
import json

from gym import kube
from gym import undo as gym_undo
from gym.undo import clean_manifest

APP_KINDS = ["deployments.apps", "daemonsets.apps", "statefulsets.apps", "services", "configmaps",
             "secrets", "networkpolicies.networking.k8s.io", "resourcequotas", "limitranges",
             "serviceaccounts", "poddisruptionbudgets.policy", "horizontalpodautoscalers.autoscaling",
             "jobs.batch", "cronjobs.batch", "pods"]
SYSTEM_OBJECTS = [("deployments.apps", "coredns"), ("configmaps", "coredns"),
                  ("daemonsets.apps", "kube-proxy"), ("configmaps", "kube-proxy")]
SYSTEM_RESTART = {"configmaps/coredns": "deployment/coredns", "configmaps/kube-proxy": "daemonset/kube-proxy"}
WEBHOOK_KINDS = ["validatingwebhookconfigurations.admissionregistration.k8s.io",
                 "mutatingwebhookconfigurations.admissionregistration.k8s.io"]
WORKLOAD_KINDS = ["deployments.apps", "daemonsets.apps", "statefulsets.apps"]
SKIP_SECRET_TYPES = {"helm.sh/release.v1", "kubernetes.io/service-account-token"}
VOLATILE_ANNOTATIONS = {"deployment.kubernetes.io/revision"}


def _tracked(kind, obj):
    if obj.get("metadata", {}).get("ownerReferences"):
        return False  # managed by a controller (ReplicaSet pods, Job pods, ...)
    if kind == "secrets" and obj.get("type") in SKIP_SECRET_TYPES:
        return False
    return True


def _norm(obj):
    o = clean_manifest(obj)
    meta = o.setdefault("metadata", {})
    ann = meta.get("annotations") or {}
    for a in VOLATILE_ANNOTATIONS:
        ann.pop(a, None)
    if ann:
        meta["annotations"] = ann
    else:
        meta.pop("annotations", None)
    return o


def _key(kind, obj):
    return f"{kind}/{obj['metadata']['name']}"


def _node_state(node):
    return {"labels": node["metadata"].get("labels", {}),
            "unschedulable": bool(node["spec"].get("unschedulable", False)),
            "taints": node["spec"].get("taints", [])}


def snapshot():
    snap = {"app": {}, "app_pods": [], "system": {}, "nodes": {}, "ns_labels": {}, "webhooks": {}}
    for kind in APP_KINDS:
        for obj in kube.items(kind, namespace=kube.APP_NS):
            if not _tracked(kind, obj):
                continue
            if kind == "pods":
                snap["app_pods"].append(obj["metadata"]["name"])
            else:
                snap["app"][_key(kind, obj)] = _norm(obj)
    for kind, name in SYSTEM_OBJECTS:
        obj = kube.get(kind, name, namespace="kube-system", missing_ok=True)
        if obj:
            snap["system"][f"{kind}/{name}"] = _norm(obj)
    for node in kube.items("nodes", namespace=None):
        snap["nodes"][node["metadata"]["name"]] = _node_state(node)
    snap["ns_labels"] = kube.get("namespace", kube.APP_NS, namespace=None)["metadata"].get("labels", {})
    for kind in WEBHOOK_KINDS:
        for obj in kube.items(kind, namespace=None):
            snap["webhooks"][_key(kind, obj)] = _norm(obj)
    return snap


def _label_patch(old, now):
    """Merge-patch body that turns label set `now` back into `old`."""
    body = {k: None for k in now if k not in old}
    body.update({k: v for k, v in old.items() if now.get(k) != v})
    return body


def _put_back(kind, saved, namespace, dry_run):
    current = kube.get(kind, saved["metadata"]["name"], namespace=namespace, missing_ok=True)
    if current is None:
        if not dry_run:
            kube.create(saved, namespace=namespace)
        return "recreated"
    if _norm(current) == saved:
        return None
    if not dry_run:
        body = copy.deepcopy(saved)
        body["metadata"]["resourceVersion"] = current["metadata"]["resourceVersion"]
        kube.kubectl("replace", "-f", "-", namespace=namespace, input=json.dumps(body))
    return "restored"


def _uses(pod_spec, name, secret):
    """Does this pod template read ConfigMap/Secret `name` (volume, envFrom or env)?"""
    for vol in pod_spec.get("volumes", []):
        if secret and (vol.get("secret") or {}).get("secretName") == name:
            return True
        if not secret and (vol.get("configMap") or {}).get("name") == name:
            return True
        for src in (vol.get("projected") or {}).get("sources", []):
            if (src.get("secret" if secret else "configMap") or {}).get("name") == name:
                return True
    ref = "secretRef" if secret else "configMapRef"
    key_ref = "secretKeyRef" if secret else "configMapKeyRef"
    for c in pod_spec.get("containers", []) + pod_spec.get("initContainers", []):
        if any((e.get(ref) or {}).get("name") == name for e in c.get("envFrom", [])):
            return True
        if any(((e.get("valueFrom") or {}).get(key_ref) or {}).get("name") == name for e in c.get("env", [])):
            return True
    return False


def restore(snap, dry_run=False):
    """Put everything back as it was in `snap`. Returns what was (or, with dry_run, would be) done."""
    actions, changed_config = [], []
    # 1. objects the agent created in the app namespace
    for kind in APP_KINDS:
        for obj in kube.items(kind, namespace=kube.APP_NS):
            if not _tracked(kind, obj):
                continue
            name = obj["metadata"]["name"]
            known = name in snap["app_pods"] if kind == "pods" else _key(kind, obj) in snap["app"]
            if not known:
                actions.append(f"delete {kind}/{name} (created during the episode)")
                if not dry_run:
                    kube.delete(kind, name, namespace=kube.APP_NS)
    # 2. app objects that were deleted or changed
    for key, saved in snap["app"].items():
        kind = key.split("/", 1)[0]
        what = _put_back(kind, saved, kube.APP_NS, dry_run)
        if what:
            actions.append(f"{what} {key}")
            if kind in ("configmaps", "secrets"):
                changed_config.append((saved["metadata"]["name"], kind == "secrets"))
    # 3. pods must re-read restored ConfigMaps/Secrets (deleting pods keeps templates exact)
    if changed_config:
        for kind in WORKLOAD_KINDS:
            for wl in kube.items(kind, namespace=kube.APP_NS):
                pod_spec = wl["spec"]["template"]["spec"]
                if any(_uses(pod_spec, n, s) for n, s in changed_config):
                    target = f"{kind.split('.')[0][:-1]}/{wl['metadata']['name']}"
                    actions.append(f"restart {target} (its config was restored)")
                    if not dry_run:
                        gym_undo.restart(target, kube.APP_NS)
    # 4. kube-system objects the scenarios touch
    for key, saved in snap["system"].items():
        kind = key.split("/", 1)[0]
        what = _put_back(kind, saved, "kube-system", dry_run)
        if what:
            actions.append(f"{what} kube-system/{key}")
            if key in SYSTEM_RESTART and not dry_run:
                gym_undo.restart(SYSTEM_RESTART[key], "kube-system")
    # 5. nodes: labels, cordon state, taints
    for node in kube.items("nodes", namespace=None):
        name = node["metadata"]["name"]
        old = snap["nodes"].get(name)
        if old is None:
            continue
        now = _node_state(node)
        body = {}
        labels = _label_patch(old["labels"], now["labels"])
        if labels:
            body["metadata"] = {"labels": labels}
        if now["unschedulable"] != old["unschedulable"]:
            body.setdefault("spec", {})["unschedulable"] = old["unschedulable"] or None
        if now["taints"] != old["taints"]:
            body.setdefault("spec", {})["taints"] = old["taints"] or None
        if body:
            actions.append(f"restored node/{name}")
            if not dry_run:
                kube.patch("node", name, body, "merge", namespace=None)
    # 6. labels on the app namespace (e.g. pod security level)
    ns = kube.get("namespace", kube.APP_NS, namespace=None)
    labels = _label_patch(snap["ns_labels"], ns["metadata"].get("labels", {}))
    if labels:
        actions.append(f"restored namespace/{kube.APP_NS} labels")
        if not dry_run:
            kube.patch("namespace", kube.APP_NS, {"metadata": {"labels": labels}}, "merge", namespace=None)
    # 7. admission webhooks
    for kind in WEBHOOK_KINDS:
        for obj in kube.items(kind, namespace=None):
            if _key(kind, obj) not in snap["webhooks"]:
                actions.append(f"delete {_key(kind, obj)} (created during the episode)")
                if not dry_run:
                    kube.delete(kind, obj["metadata"]["name"], namespace=None)
    for key, saved in snap["webhooks"].items():
        what = _put_back(key.split("/", 1)[0], saved, None, dry_run)
        if what:
            actions.append(f"{what} {key}")
    return actions
