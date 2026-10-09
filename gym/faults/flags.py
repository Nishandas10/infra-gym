"""Application-level faults via the demo's built-in feature flags (flagd).

In demo 3.x flagd reads /etc/flagd/demo.flagd.json from an emptyDir that an
init container fills from the flagd-config ConfigMap once, at pod start.
Editing the ConfigMap therefore changes nothing until flagd restarts. The live
file is shared with the flagd-ui container (at /app/data), which is how the
Feature Flags UI toggles flags; flagd hot-reloads it. We edit that file.
"""
from __future__ import annotations

import json
import time

from .. import kube, toolbox
from . import mechanism

FLAGD = "deploy/flagd"
UI_CONTAINER = "flagd-ui"
LIVE_FILE = "/app/data/demo.flagd.json"
OFREP = "http://flagd.default.svc.cluster.local:8016/ofrep/v1/evaluate/flags/"


def read_config():
    r = kube.exec_in(FLAGD, ["cat", LIVE_FILE], container=UI_CONTAINER)
    if r.returncode != 0:
        raise kube.KubeError(f"cannot read {LIVE_FILE}: {r.stderr.strip()}")
    return r.stdout


def write_config(text):
    r = kube.exec_in(FLAGD, ["sh", "-c", f"cat > {LIVE_FILE}"], container=UI_CONTAINER, input=text)
    if r.returncode != 0:
        raise kube.KubeError(f"cannot write {LIVE_FILE}: {r.stderr.strip()}")


def evaluate(flag, context=None):
    """What flagd currently returns for a flag, as the services see it (OFREP API)."""
    r = toolbox.http(OFREP + flag, method="POST", body={"context": context or {}})
    return json.loads(r["body"]) if r["status"] == 200 else {"error": r["status"], "body": r["body"][:200]}


def set_variant(config_text, flag, variant):
    """Return new config text with `flag` switched to `variant`.

    Flags with targeting rules (e.g. productCatalogFailure only fails for one
    product) are switched by changing the targeted branch of the rule, which is
    what the Feature Flags UI does; the rest by changing defaultVariant.
    """
    cfg = json.loads(config_text)
    f = cfg["flags"].get(flag)
    if f is None:
        raise KeyError(f"unknown flag {flag!r}; known: {', '.join(sorted(cfg['flags']))}")
    if variant not in f["variants"]:
        raise KeyError(f"flag {flag} has no variant {variant!r}; variants: {list(f['variants'])}")
    rule = (f.get("targeting") or {}).get("if")
    if isinstance(rule, list) and len(rule) == 3:
        rule[1] = variant
    else:
        f["defaultVariant"] = variant
    return json.dumps(cfg, indent=2) + "\n"


def targeting_context(config_text, flag):
    """A context that hits the targeted branch of a flag's rule (e.g. product_id=OLJCESPC7Z)."""
    f = json.loads(config_text)["flags"][flag]
    rule = (f.get("targeting") or {}).get("if")
    try:
        (var, value), = [(c["=="][0]["var"], c["=="][1]) for c in [rule[0]]]
        return {var: value}
    except Exception:
        return {}


@mechanism("feature_flag", "application", "Turn on one of the demo's built-in failure flags")
def feature_flag(fault, undo, ctx):
    flag, variant = fault["flag"], str(fault.get("variant", "on"))
    original = read_config()
    undo.on_revert_exec(FLAGD, ["sh", "-c", f"cat > {LIVE_FILE}"], container=UI_CONTAINER, stdin=original)
    write_config(set_variant(original, flag, variant))
    context = targeting_context(original, flag)
    got = kube.wait_until(lambda: evaluate(flag, context).get("variant") == variant, timeout=30, interval=2)
    if not got:
        raise RuntimeError(f"flagd did not pick up {flag}={variant}: {evaluate(flag, context)}")


# ------------------------------------------------- the flag's source of truth
CONFIGMAP = "flagd-config"
CONFIG_KEY = "demo.flagd.json"


def set_source_variant(flag, variant, configmap=CONFIGMAP, key=CONFIG_KEY):
    """Change a flag in the flagd-config ConfigMap (what flagd loads at pod start).
    Returns the original ConfigMap text."""
    obj = kube.get("configmap", configmap)
    text = obj["data"][key]
    kube.patch("configmap", configmap, {"data": {key: set_variant(text, flag, variant)}}, "merge")
    return text


@mechanism("flag_in_source_config", "application",
           "Change a flag in the flagd-config ConfigMap (the source of truth) and restart flagd so it loads it; "
           "fixing only the live file does not survive the next flagd restart")
def flag_in_source_config(fault, undo, ctx):
    from ..undo import restart
    flag, variant = fault["flag"], str(fault.get("variant", "on"))
    name, key = fault.get("configmap", CONFIGMAP), fault.get("key", CONFIG_KEY)
    # Recorded first, so on revert it runs last: restore the ConfigMap, then restart flagd,
    # whose init container rebuilds the live file from the restored ConfigMap.
    undo.on_revert_restart("deployment/flagd")
    obj = undo.snapshot("configmap", name, [f"/data/{kube.escape(key)}"])
    text = obj["data"][key]
    kube.patch("configmap", name, {"data": {key: set_variant(text, flag, variant)}}, "merge")
    # The kubelet can hand a pod started right after the edit the cached old ConfigMap.
    time.sleep(fault.get("restart_delay_s", 20))
    restart("deployment/flagd")
    context = targeting_context(text, flag)
    got = kube.wait_until(lambda: evaluate(flag, context).get("variant") == variant,
                          timeout=fault.get("load_timeout_s", 180), interval=5)
    if not got:
        raise RuntimeError(f"flagd did not load {flag}={variant} from the ConfigMap: {evaluate(flag, context)}")
