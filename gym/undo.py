"""Per-scenario undo log, so every injection can be reverted exactly.

Each fault records what it changed before changing it. Reverting replays those
records in reverse order. The log lives in .gym_state/<cluster>/<scenario-id>.json, so a revert
still works from a new terminal or after a crash. <cluster> is the KUBECONFIG file's name (`default` without
one), so the same scenario can run on several clusters at once without one run reverting another's fault.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess

from . import kube

STATE_DIR = pathlib.Path(__file__).resolve().parents[1] / ".gym_state"


def cluster_key():
    """Which cluster this process works on: its KUBECONFIG file's name (one per parallel worker)."""
    cfg = os.environ.get("KUBECONFIG", "").split(os.pathsep)[0]
    return re.sub(r"[^\w.-]", "_", pathlib.Path(cfg).name) if cfg else "default"


# Server-managed fields that must not be sent back when recreating an object.
_RUNTIME_META = ("uid", "resourceVersion", "creationTimestamp", "generation", "managedFields", "selfLink")


def clean_manifest(obj):
    obj = json.loads(json.dumps(obj))
    obj.pop("status", None)
    meta = obj.get("metadata", {})
    for key in _RUNTIME_META:
        meta.pop(key, None)
    ann = meta.get("annotations") or {}
    ann.pop("kubectl.kubernetes.io/last-applied-configuration", None)
    if obj.get("kind") == "Service":
        obj.get("spec", {}).pop("clusterIP", None)
        obj.get("spec", {}).pop("clusterIPs", None)
    return obj


class UndoLog:
    def __init__(self, scenario_id):
        self.scenario_id = scenario_id
        self.path = STATE_DIR / cluster_key() / f"{scenario_id}.json"
        legacy = STATE_DIR / f"{scenario_id}.json"     # written before logs were kept per cluster
        if not self.path.exists() and legacy.exists() and cluster_key() == "default":
            self.path = legacy
        self.actions = json.loads(self.path.read_text()) if self.path.exists() else []

    @property
    def active(self):
        return bool(self.actions)

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.actions, indent=1))

    def add(self, action):
        self.actions.append(action)
        self._save()

    # ---------------------------------------------------------- recording helpers
    def snapshot(self, kind, name, pointers, namespace=kube.APP_NS):
        """Remember the current value (or absence) of each JSON pointer."""
        obj = kube.get(kind, name, namespace=namespace)
        fields = {}
        for p in pointers:
            exists, value = kube.pointer_get(obj, p)
            fields[p] = {"exists": exists, "value": value}
        self.add({"op": "restore", "kind": kind, "name": name, "ns": namespace, "fields": fields})
        return obj

    def created(self, kind, name, namespace=kube.APP_NS):
        self.add({"op": "delete", "kind": kind, "name": name, "ns": namespace})

    def deleted(self, obj, namespace=kube.APP_NS):
        self.add({"op": "recreate", "ns": namespace, "manifest": clean_manifest(obj)})

    def on_revert_exec(self, target, cmd, namespace=kube.APP_NS, container=None, stdin=None):
        self.add({"op": "exec", "target": target, "ns": namespace, "container": container, "cmd": cmd, "stdin": stdin})

    def on_revert_local(self, cmd):
        self.add({"op": "local", "cmd": cmd})

    def on_revert_restart(self, target, namespace=kube.APP_NS):
        """After restoring config, restart what reads it: 'deployment/x' / 'daemonset/x' or a pod selector."""
        self.add({"op": "restart", "target": target, "ns": namespace})

    # ---------------------------------------------------------------- reverting
    def revert(self):
        """Undo everything, newest first. Returns a list of error strings (empty = clean)."""
        errors = []
        for action in reversed(self.actions):
            try:
                _undo(action)
            except Exception as e:  # keep going: undo as much as possible
                errors.append(f"{action['op']} {action.get('kind', '')} {action.get('name', '')}: {e}")
        if not errors:
            self.actions = []
            self.path.unlink(missing_ok=True)
        return errors


def run_hook(hook):
    """Extra clean-up steps some scenarios need after their changes are undone."""
    import time
    if hook.get("delete_failed_pods"):
        kube.kubectl("delete", "pods", "--field-selector=status.phase=Failed", "--wait=false")
    if hook.get("prune_replicasets"):
        # k8s.bad_rollout: the revisions it created, once the Deployment's template is restored. The one the
        # Deployment runs now is kept, whatever its name (the agent may have rolled out more revisions).
        h = hook["prune_replicasets"]
        from .faults.workload import owned_replicasets

        def synced():   # the controller has seen the restored template and named its revision
            d = kube.get("deployment", h["deployment"], namespace=h["ns"])
            gen = d["metadata"].get("generation", 0)
            return d if (d.get("status") or {}).get("observedGeneration", gen) >= gen else None
        dep = kube.wait_until(synced, 60, interval=2) or kube.get("deployment", h["deployment"], namespace=h["ns"])
        current = (dep["metadata"].get("annotations") or {}).get("deployment.kubernetes.io/revision")
        for rs in owned_replicasets(h["deployment"], h["ns"]):
            rev = (rs["metadata"].get("annotations") or {}).get("deployment.kubernetes.io/revision")
            if rs["metadata"]["name"] not in h["keep"] and rev != current:
                kube.delete("replicaset", rs["metadata"]["name"], namespace=h["ns"])
    if hook.get("kafka_topic"):
        # A fresh broker has no topics until someone produces; consumers that subscribe
        # before that can sit idle for minutes. Create it as soon as the broker answers.
        from . import toolbox
        deadline = time.time() + 240
        while True:
            r = toolbox.kafka("kafka-topics.sh", "--create", "--if-not-exists", "--topic", hook["kafka_topic"],
                              "--partitions", "1", "--replication-factor", "1", timeout=90)
            if r.returncode == 0:
                break
            if time.time() > deadline:
                raise RuntimeError(f"could not create topic {hook['kafka_topic']}: {r.stderr[-200:]}")
            time.sleep(10)


def restart(target, namespace=kube.APP_NS):
    """'deployment/x' or 'daemonset/x' -> delete its pods; anything else is a pod label selector.

    Deleting the pods (instead of `kubectl rollout restart`) leaves the pod
    template untouched, so restores stay exact.
    """
    if "/" in target and "=" not in target:
        kind, name = target.split("/", 1)
        obj = kube.get(kind, name, namespace=namespace)
        labels = obj["spec"]["selector"].get("matchLabels", {})
        target = ",".join(f"{k}={v}" for k, v in labels.items())
    kube.kubectl("delete", "pod", "-l", target, "--wait=false", namespace=namespace)


def _undo(a):
    op = a["op"]
    if op == "restore":
        current = kube.get(a["kind"], a["name"], namespace=a["ns"], missing_ok=True)
        if current is None:
            raise kube.KubeError("object no longer exists")
        ops = []
        for pointer, f in a["fields"].items():
            now_exists, _ = kube.pointer_get(current, pointer)
            if f["exists"]:
                ops.append({"op": "replace" if now_exists else "add", "path": pointer, "value": f["value"]})
            elif now_exists:
                ops.append({"op": "remove", "path": pointer})
        if ops:
            kube.patch(a["kind"], a["name"], ops, "json", namespace=a["ns"])
    elif op == "delete":
        kube.delete(a["kind"], a["name"], namespace=a["ns"])
    elif op == "recreate":
        m = a["manifest"]
        if kube.get(m["kind"], m["metadata"]["name"], namespace=a["ns"], missing_ok=True) is None:
            kube.create(m, namespace=a["ns"])
    elif op == "exec":
        r = kube.exec_in(a["target"], a["cmd"], namespace=a["ns"], container=a.get("container"), input=a.get("stdin"))
        if r.returncode != 0:
            raise kube.KubeError(r.stderr.strip() or r.stdout.strip())
    elif op == "local":
        r = subprocess.run(a["cmd"], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip())
    elif op == "restart":
        restart(a["target"], a["ns"])
    elif op == "hook":
        run_hook(a["hook"])
    else:
        raise ValueError(f"unknown undo op {op}")
