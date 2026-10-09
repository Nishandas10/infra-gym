"""Offline test of the Hard tier: inject + exact revert of every scenarios/hard-* spec against an
in-memory fake cluster. Catches broken paths, $name lookups, snapshot/undo mistakes and ordering
bugs before anything touches the real cluster. It does NOT prove the faults behave as intended on
the live shop; that is what scripts/validate_scenario.py on the VM is for.

usage: python tests/test_hard_offline.py        (needs: pip install jsonpatch)
"""
import copy
import json
import pathlib
import sys
import time

import jsonpatch

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from gym import kube, undo as undo_mod  # noqa: E402
from gym import faults  # noqa: E402
from gym.faults import flags  # noqa: E402
from gym.spec import load  # noqa: E402

time.sleep = lambda s: None  # no waiting in tests

KINDS = {"deployment": "deployments", "deploy": "deployments", "deployments": "deployments",
         "deployments.apps": "deployments", "service": "services", "services": "services",
         "configmap": "configmaps", "configmaps": "configmaps", "secret": "secrets", "secrets": "secrets",
         "node": "nodes", "nodes": "nodes", "daemonset": "daemonsets", "daemonsets": "daemonsets",
         "namespace": "namespaces", "pods": "pods", "pod": "pods",
         "endpointslices.discovery.k8s.io": "endpointslices", "endpointslice": "endpointslices"}


def kind_of(k):
    return KINDS.get(k.lower(), k.lower() + ("" if k.endswith("s") else "s"))


class Fake:
    def __init__(self):
        self.objs = {}
        self.execs = []
        self.deleted_pods = []
        flagd_cfg = {"flags": {
            "paymentFailure": {"defaultVariant": "off", "state": "ENABLED",
                               "variants": {"100%": 1, "50%": 0.5, "off": 0}},
            "adFailure": {"defaultVariant": "off", "state": "ENABLED", "variants": {"on": True, "off": False}}}}
        self.flagd_live = json.dumps(flagd_cfg, indent=2)
        for name, env in {
            "payment": {"PAYMENT_PORT": "8080"}, "cart": {"VALKEY_ADDR": "valkey-cart:6379"},
            "checkout": {"PRODUCT_CATALOG_ADDR": "product-catalog:8080", "PAYMENT_ADDR": "payment:8080"},
            "recommendation": {"PRODUCT_CATALOG_ADDR": "product-catalog:8080"}, "ad": {},
            "shipping": {"QUOTE_ADDR": "http://quote:8080", "SHIPPING_PORT": "8080"}, "quote": {},
            "product-catalog": {}, "valkey-cart": {}, "astronomy-db": {}, "accounting": {}, "email": {},
            "currency": {}, "flagd": {}, "frontend": {}}.items():
            self.put("deployments", name, {
                "apiVersion": "apps/v1", "kind": "Deployment",
                "metadata": {"name": name, "namespace": "default", "annotations": {"deployment.kubernetes.io/revision": "1"}},
                "spec": {"replicas": 1, "selector": {"matchLabels": {"opentelemetry.io/name": name}},
                         "strategy": {"type": "RollingUpdate"},
                         "template": {"metadata": {"labels": {"opentelemetry.io/name": name,
                                                              "app.kubernetes.io/name": name}},
                                      "spec": {"containers": [{
                                          "name": name, "image": f"demo:{name}",
                                          "env": [{"name": "OTEL_SERVICE_NAME", "value": name}] +
                                                 [{"name": k, "value": v} for k, v in env.items()],
                                          "resources": {"limits": {"memory": "300Mi"}},
                                          "ports": [{"containerPort": 8080, "name": "service"}]}]}}}})
            self.put("pods", f"{name}-abc", {"kind": "Pod", "metadata": {
                "name": f"{name}-abc", "labels": {"opentelemetry.io/name": name}},
                "spec": {"containers": [{"name": name, "ports": [{"containerPort": 8080, "name": "service"}]}]}})
        for name in ("quote", "shipping", "payment", "product-catalog", "email"):
            self.put("services", name, {"apiVersion": "v1", "kind": "Service", "metadata": {"name": name},
                                        "spec": {"selector": {"opentelemetry.io/name": name},
                                                 "ports": [{"name": "tcp-service", "port": 8080,
                                                            "targetPort": 8080 if name != "quote" else "service"}]}})
        self.put("configmaps", "flagd-config", {"kind": "ConfigMap", "metadata": {"name": "flagd-config"},
                                                "data": {"demo.flagd.json": self.flagd_live}})
        self.put("configmaps", "otel-collector-agent", {"kind": "ConfigMap", "metadata": {"name": "otel-collector-agent"},
                                                        "data": {"relay": "exporters:\n  otlp:\n    endpoint: jaeger:4317\n"}})
        self.put("daemonsets", "otel-collector-agent", {"kind": "DaemonSet", "metadata": {"name": "otel-collector-agent"},
                                                        "spec": {"selector": {"matchLabels": {"app": "otel-agent"}},
                                                                 "template": {"spec": {}}}})
        for n in ("ai-gym-worker", "ai-gym-worker2"):
            self.put("nodes", n, {"kind": "Node", "metadata": {"name": n, "labels": {}}, "spec": {}})
        self.flagd_loaded = self.flagd_live

    # storage
    def put(self, kind, name, obj):
        self.objs[(kind_of(kind), name)] = obj

    def state(self):
        out = {k: v for k, v in copy.deepcopy(self.objs).items() if k[0] != "pods"}
        for (kind, _), o in out.items():
            if kind == "deployments":
                o["metadata"].get("annotations", {}).pop("deployment.kubernetes.io/revision", None)
        return out

    # kube API
    def get(self, kind, name=None, namespace="default", selector=None, missing_ok=False):
        k = kind_of(kind)
        if name:
            o = self.objs.get((k, name))
            if o is None:
                if missing_ok:
                    return None
                raise kube.KubeError(f"NotFound {k}/{name}")
            return copy.deepcopy(o)
        items = [copy.deepcopy(o) for (kk, _), o in self.objs.items() if kk == k]
        if selector:
            want = dict(p.split("=", 1) for p in selector.split(","))
            items = [o for o in items if all(o["metadata"].get("labels", {}).get(a) == b for a, b in want.items())]
        return {"items": items}

    def apply(self, manifest, namespace="default"):
        for d in (manifest if isinstance(manifest, list) else [manifest]):
            d = copy.deepcopy(d)
            if d["kind"] == "Secret" and "stringData" in d:
                d.setdefault("data", {}).update(d.pop("stringData"))
            self.put(d["kind"], d["metadata"]["name"], d)
        return ""

    def delete(self, kind, name, namespace="default", wait=False, force=False):
        self.objs.pop((kind_of(kind), name), None)
        return ""

    def patch(self, kind, name, body, patch_type="strategic", namespace="default"):
        k = kind_of(kind)
        obj = self.objs[(k, name)]
        if patch_type == "json":
            self.objs[(k, name)] = jsonpatch.apply_patch(obj, body)
        else:
            self.objs[(k, name)] = merge(obj, body, strategic=(patch_type == "strategic"))
        return ""

    def kubectl(self, *args, namespace="default", input=None, timeout=90):
        if args[:2] == ("delete", "pod"):
            self.deleted_pods.append(args[3] if len(args) > 3 else "")
            if "flagd" in " ".join(map(str, args)):   # flagd restart: live file rebuilt from the ConfigMap
                self.flagd_loaded = self.objs[("configmaps", "flagd-config")]["data"]["demo.flagd.json"]
            return ""
        return ""

    def exec_in(self, target, cmd, namespace="default", container=None, input=None, timeout=90):
        self.execs.append((target, cmd))

        class R:
            returncode, stdout, stderr = 0, "", ""
        return R()


def merge(base, patch, strategic):
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


def install(fake):
    for fn in ("get", "apply", "delete", "patch", "kubectl", "exec_in"):
        setattr(kube, fn, getattr(fake, fn))
    kube.items = lambda kind, namespace="default", selector=None: fake.get(kind, namespace=namespace,
                                                                            selector=selector)["items"]
    kube.wait_until = lambda fn, timeout, interval=5: fn()

    def evaluate(flag, context=None):
        cfg = json.loads(fake.flagd_loaded)["flags"][flag]
        return {"variant": cfg["defaultVariant"]}
    flags.evaluate = evaluate
    undo_mod.STATE_DIR = REPO / ".gym_state_test"


def env_of(fake, dep):
    return fake.objs[("deployments", dep)]["spec"]["template"]["spec"]["containers"][0]["env"]


EXPECT = {   # what must be true right after injection
    "hard-fix-reverted-by-cronjob-101": lambda f: (
        {"name": "PAYMENT_PORT", "value": "8081"} in env_of(f, "payment")
        and ("cronjobs", "payment-config-sync") in f.objs and ("roles", "config-sync") in f.objs),
    "hard-egress-policy-blocks-db-102": lambda f: (
        ("networkpolicys", "product-catalog-egress-hardening") in f.objs
        and ("jobs", "astronomy-db-backup-nightly") in f.objs),
    "hard-cart-chained-addr-auth-103": lambda f: (
        {"name": "VALKEY_ADDR", "value": "valkey-cart:6380"} in env_of(f, "cart")
        and any("requirepass" in c for _, c in f.execs) and ("secrets", "valkey-cart-credentials") in f.objs),
    "hard-ghost-legacy-email-pods-104": lambda f: ("deployments", "email-v1-legacy") in f.objs,
    "hard-silent-ledger-write-denied-105": lambda f: any("REVOKE INSERT" in " ".join(c) for _, c in f.execs),
    "hard-allowlist-forgets-checkout-106": lambda f: (
        ("networkpolicys", "product-catalog-allow-clients") in f.objs
        and f.objs[("deployments", "payment")]["metadata"]["annotations"].get("kubernetes.io/change-cause")),
    "hard-masked-second-fault-107": lambda f: (
        f.objs[("services", "shipping")]["spec"]["ports"][0]["targetPort"] == 8888
        and {"name": "PRODUCT_CATALOG_ADDR", "value": "product-catalog:9090"} in env_of(f, "checkout")),
    "hard-pinned-endpoints-108": lambda f: (
        "selector" not in f.objs[("services", "quote")]["spec"]
        and f.objs[("endpointslices", "quote-pinned")]["ports"][0]["port"] == 8080
        and f.objs[("endpointslices", "quote-pinned")]["ports"][0]["name"] == "tcp-service"),
    "hard-duplicate-env-override-109": lambda f: (
        [e["value"] for e in env_of(f, "recommendation") if e["name"] == "PRODUCT_CATALOG_ADDR"]
        == ["product-catalog:8080", "product-catalog:3550"]
        and f.objs[("deployments", "recommendation")]["spec"]["template"]["spec"]["containers"][0]["envFrom"]),
    "hard-oom-fix-blocked-by-limitrange-110": lambda f: (
        f.objs[("deployments", "ad")]["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] == "48Mi"
        and ("limitranges", "namespace-container-limits") in f.objs),
    "hard-flag-in-source-of-truth-111": lambda f: (
        json.loads(f.objs[("configmaps", "flagd-config")]["data"]["demo.flagd.json"])["flags"]["paymentFailure"]
        ["defaultVariant"] == "50%" and json.loads(f.flagd_loaded)["flags"]["paymentFailure"]["defaultVariant"] == "50%"),
    "hard-telemetry-noise-hides-scheduling-112": lambda f: (
        "jaeger:4999" in f.objs[("configmaps", "otel-collector-agent")]["data"]["relay"]
        and f.objs[("nodes", "ai-gym-worker2")]["spec"]["taints"][0]["key"] == "dedicated"),
}


def main():
    specs = sorted((REPO / "scenarios").glob("hard-*/spec.yaml"))
    assert len(specs) == len(EXPECT), f"{len(specs)} specs vs {len(EXPECT)} expectations"
    failures = 0
    for p in specs:
        fake = Fake()
        install(fake)
        spec, sdir = load(p)
        before = fake.state()
        try:
            faults.inject(spec, sdir)
            assert EXPECT[spec["id"]](fake), "injected state not as expected"
            errors = faults.revert(spec)
            assert not errors, f"revert errors: {errors}"
            after = fake.state()
            if after != before:
                diff = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
                raise AssertionError(f"not restored exactly: {diff}")
            if spec["id"] == "hard-flag-in-source-of-truth-111":
                assert json.loads(fake.flagd_loaded)["flags"]["paymentFailure"]["defaultVariant"] == "off", \
                    "flagd not restarted after the ConfigMap was restored"
            print(f"ok    {spec['id']}")
        except Exception as e:
            failures += 1
            print(f"FAIL  {spec['id']}: {type(e).__name__}: {e}")
        finally:
            for f in (REPO / ".gym_state_test").glob("*.json"):
                f.unlink()
    print(f"\n{len(specs) - failures}/{len(specs)} Hard scenarios inject and revert exactly (offline)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
