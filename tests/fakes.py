"""An in-memory fake cluster for offline tests of fault injection and exact revert.

It is loaded from tests/fixtures/world.json, a snapshot of the healthy live world taken by
scripts/dump_world_fixture.py, so faults run against the real object shapes. It implements the
parts of gym.kube that fault mechanisms and the undo log use, plus flagd's live flag file and
Chaos Mesh's "AllInjected" status.

It proves that injection works on the real objects and that revert restores them exactly. It
does not prove a fault behaves as intended on the live shop; scripts/validate_scenario.py does.
"""
from __future__ import annotations

import copy
import json
import pathlib

import jsonpatch

from gym import kube, toolbox
from gym import undo as undo_mod
from gym.faults import flags

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "world.json"

CLUSTER_SCOPED = {"node", "namespace", "validatingwebhookconfiguration", "mutatingwebhookconfiguration",
                  "clusterrole", "clusterrolebinding", "priorityclass", "storageclass", "persistentvolume"}
ALIASES = {"deploy": "deployment", "svc": "service", "cm": "configmap", "ds": "daemonset", "sts": "statefulset",
           "ns": "namespace", "no": "node", "po": "pod", "netpol": "networkpolicy", "endpoints": "endpoints"}
VOLATILE_ANNOTATIONS = ("deployment.kubernetes.io/revision",)


def canonical_kind(kind):
    """'deployments.apps', 'Deployment', 'deploy' -> 'deployment'; 'NetworkChaos' -> 'networkchaos'."""
    k = kind.lower().split(".", 1)[0]
    if k in ALIASES:
        return ALIASES[k]
    if k.endswith("chaos"):
        return k
    if k.endswith("ies"):
        return k[:-3] + "y"
    if k.endswith("s"):
        return k[:-1]
    return k


def _key(kind, name, namespace):
    k = canonical_kind(kind)
    return (k, None if k in CLUSTER_SCOPED else (namespace or kube.APP_NS), name)


def _matches(obj, selector):
    """Equality-based label selectors: key=value, key!=value, key, !key (comma-separated)."""
    if not selector:
        return True
    labels = obj.get("metadata", {}).get("labels") or {}
    for term in selector.split(","):
        if "!=" in term:
            key, value = term.split("!=", 1)
            ok = labels.get(key) != value
        elif "=" in term:
            key, value = term.split("=", 1)
            ok = labels.get(key) == value
        elif term.startswith("!"):
            ok = term[1:] not in labels
        else:
            ok = term in labels
        if not ok:
            return False
    return True


def merge(base, patch, strategic):
    """Merge patch, plus the one strategic-merge rule the faults rely on: containers merge by name."""
    if isinstance(base, dict) and isinstance(patch, dict):
        out = copy.deepcopy(base)
        for k, v in patch.items():
            if v is None:
                out.pop(k, None)
            elif k == "containers" and strategic and isinstance(v, list):
                cur = {c["name"]: c for c in out.get(k, [])}
                for c in v:
                    cur[c["name"]] = merge(cur.get(c["name"], {}), c, strategic)
                out[k] = list(cur.values())
            else:
                out[k] = merge(out.get(k), v, strategic)
        return out
    return copy.deepcopy(patch)


class Result:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


class FakeCluster:
    def __init__(self, fixture=FIXTURE):
        data = json.loads(pathlib.Path(fixture).read_text())
        self.objs = {}
        for o in data["objects"]:
            self.objs[_key(o["kind"], o["metadata"]["name"], o["metadata"].get("namespace"))] = o
        self.flagd_live = data["flagd_live_file"]
        self.execs = []           # (target, cmd, stdin)
        self.node_cmds = []       # (node, cmd) run with kube.node_exec (docker exec into a kind node)
        self.kubelet_stopped = set()
        self.pod_deletions = []   # label selectors / args of `kubectl delete pod(s)`
        # The fixture keeps no pod placement or status: spread the pods over the workers, all Ready.
        workers = self.workers()
        for i, key in enumerate(sorted(k for k in self.objs if k[0] == "pod")):
            pod = self.objs[key]
            pod.setdefault("spec", {})["nodeName"] = workers[i % len(workers)]
            pod["status"] = {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}]}

    # ------------------------------------------------------------- inspection
    def obj(self, kind, name, namespace=kube.APP_NS):
        return self.objs.get(_key(kind, name, namespace))

    def state(self):
        """Every object except pods, normalised the way a restore is judged (clean_manifest)."""
        out = {}
        for key, o in self.objs.items():
            if key[0] == "pod":
                continue
            c = undo_mod.clean_manifest(o)
            ann = c.get("metadata", {}).get("annotations")
            if ann:
                for a in VOLATILE_ANNOTATIONS:
                    ann.pop(a, None)
                if not ann:
                    c["metadata"].pop("annotations")
            out[key] = c
        return out

    def workers(self, schedulable=False):
        nodes = [o for k, o in sorted(self.objs.items()) if k[0] == "node"]
        return [n["metadata"]["name"] for n in nodes
                if "node-role.kubernetes.io/control-plane" not in (n["metadata"].get("labels") or {})
                and not any(t.get("key") == "node-role.kubernetes.io/control-plane" for t in n["spec"].get("taints", []))
                and not (schedulable and n["spec"].get("unschedulable"))]

    def node_of(self, selector):
        return {p["spec"]["nodeName"] for p in self.items("pod", selector=selector)}

    def flags_live(self):
        return json.loads(self.flagd_live)["flags"]

    def flags_source(self):
        cm = self.obj("configmap", flags.CONFIGMAP)
        return json.loads(cm["data"][flags.CONFIG_KEY])["flags"]

    # ---------------------------------------------------------------- kube API
    def get(self, kind, name=None, namespace=kube.APP_NS, selector=None, missing_ok=False):
        if name:
            o = self.objs.get(_key(kind, name, namespace))
            if o is None:
                if missing_ok:
                    return None
                raise kube.KubeError(f"NotFound {canonical_kind(kind)}/{name}")
            return copy.deepcopy(o)
        k = canonical_kind(kind)
        ns = None if k in CLUSTER_SCOPED else (namespace or kube.APP_NS)
        return {"items": [copy.deepcopy(o) for (kk, nn, _), o in sorted(self.objs.items(), key=lambda x: str(x[0]))
                          if kk == k and nn == ns and _matches(o, selector)]}

    def items(self, kind, namespace=kube.APP_NS, selector=None):
        return self.get(kind, namespace=namespace, selector=selector)["items"]

    def _store(self, doc, namespace):
        doc = copy.deepcopy(doc)
        ns = doc.get("metadata", {}).get("namespace") or namespace
        if doc["kind"] == "Secret" and "stringData" in doc:
            doc.setdefault("data", {}).update(doc.pop("stringData"))
        if doc.get("apiVersion", "").startswith("chaos-mesh.org/"):
            doc["status"] = {"conditions": [{"type": "AllInjected", "status": "True"}]}
        self.objs[_key(doc["kind"], doc["metadata"]["name"], ns)] = doc

    def apply(self, manifest, namespace=kube.APP_NS):
        for d in (manifest if isinstance(manifest, list) else [manifest]):
            self._store(d, namespace)
        return ""

    def create(self, manifest, namespace=kube.APP_NS):
        key = _key(manifest["kind"], manifest["metadata"]["name"], manifest["metadata"].get("namespace") or namespace)
        if key in self.objs:
            raise kube.KubeError(f"AlreadyExists {key}")
        self._store(manifest, namespace)
        return ""

    def delete(self, kind, name, namespace=kube.APP_NS, wait=False, force=False):
        self.objs.pop(_key(kind, name, namespace), None)
        return ""

    def patch(self, kind, name, body, patch_type="strategic", namespace=kube.APP_NS):
        key = _key(kind, name, namespace)
        if key not in self.objs:
            raise kube.KubeError(f"NotFound {key}")
        if patch_type == "json":
            self.objs[key] = jsonpatch.apply_patch(self.objs[key], body)
        else:
            self.objs[key] = merge(self.objs[key], body, strategic=(patch_type == "strategic"))
        return ""

    def kubectl(self, *args, namespace=kube.APP_NS, input=None, timeout=90):
        args = [str(a) for a in args]
        if args[:1] == ["delete"] and len(args) > 1 and canonical_kind(args[1]) == "pod":
            self.pod_deletions.append(" ".join(args[2:]))
            if "-l" in args:   # the replacement pods land on a schedulable worker, another one if possible
                selector = args[args.index("-l") + 1]
                for key, pod in self.objs.items():
                    if key[0] == "pod" and key[1] == namespace and _matches(pod, selector):
                        free = self.workers(schedulable=True)
                        others = [n for n in free if n != pod["spec"]["nodeName"]]
                        if others or free:
                            pod["spec"]["nodeName"] = (others or free)[0]
            if any("flagd" in a for a in args):
                # flagd's init container rebuilds the live file from the ConfigMap at pod start
                self.flagd_live = self.obj("configmap", flags.CONFIGMAP)["data"][flags.CONFIG_KEY]
        return ""

    def exec_in(self, target, cmd, namespace=kube.APP_NS, container=None, input=None, timeout=90):
        cmd = list(cmd)
        self.execs.append((target, cmd, input))
        if target == flags.FLAGD and cmd == ["cat", flags.LIVE_FILE]:
            return Result(self.flagd_live)
        if target == flags.FLAGD and cmd == ["sh", "-c", f"cat > {flags.LIVE_FILE}"]:
            self.flagd_live = input
        return Result()

    def node_exec(self, node, cmd, timeout=60):
        cmd = list(cmd)
        self.node_cmds.append((node, cmd))
        if cmd[:2] == ["systemctl", "stop"] and cmd[2:] == ["kubelet"]:
            self.kubelet_stopped.add(node)
        if cmd[:2] == ["systemctl", "start"] and cmd[2:] == ["kubelet"]:
            self.kubelet_stopped.discard(node)
        return ""

    def node_ready(self, node):
        return node not in self.kubelet_stopped

    # ------------------------------------------------------- what services see
    def evaluate(self, flag, context=None):
        f = self.flags_live()[flag]
        rule = (f.get("targeting") or {}).get("if")
        if context and isinstance(rule, list) and len(rule) == 3:
            return {"variant": rule[1]}
        return {"variant": f["defaultVariant"]}


def install(fake, monkeypatch, state_dir):
    """Route gym.kube (and the few helpers that reach the network) to the fake."""
    for fn in ("get", "items", "apply", "create", "delete", "patch", "kubectl", "exec_in", "node_exec", "node_ready"):
        monkeypatch.setattr(kube, fn, getattr(fake, fn))
    monkeypatch.setattr(kube, "wait_until", lambda fn, timeout, interval=5: fn())
    monkeypatch.setattr(flags, "evaluate", fake.evaluate)
    monkeypatch.setattr(toolbox, "kafka", lambda *a, **k: Result())
    monkeypatch.setattr(undo_mod, "STATE_DIR", state_dir)
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)
