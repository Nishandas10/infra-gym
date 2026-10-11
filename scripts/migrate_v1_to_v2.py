"""One-off: convert the spec-v1 scenarios into v2 templates (templates/<family>/<id>/).

usage: python scripts/migrate_v1_to_v2.py     (run once, before scripts/generate.py)

Sources:
  scenarios/<id>/spec.yaml                  every v1 spec
  scenarios/<id>/reference_solution.md      copied for the hand-written (golden) scenarios
  scenarios/<id>/chaos.yaml                 copied next to the template
  gym/catalog.py                            cause + diagnosis steps of the generated scenarios
  scripts/build_hard_scenarios.py           cause, diagnosis, traps and noise of the Hard tier

Checks before writing anything: every template validates, and the reference_solution.md that
the generator will produce is byte-identical to today's for every generated scenario.
Deleted together with the v1 generators once the migration is committed.
"""
import importlib.util
import pathlib
import shutil
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from gym.core import generate  # noqa: E402
from gym.core.schema import Template  # noqa: E402
from gym.faults import ALIASES  # noqa: E402

SCEN = REPO / "scenarios"
DEFAULTS = yaml.safe_load((REPO / "templates" / "defaults.yaml").read_text())

# Comments from the v1 YAML specs and from gym/catalog.py / build_hard_scenarios.py, kept as data
# so they survive templates being rewritten by tools.
NOTES = {
    "cache-leak-009": [
        "Memory check: baseline is ~50Mi and ~90ms. Leaked memory never shrinks without a restart, which "
        "makes it a steadier signal than latency (which depends on how much traffic arrives).",
        "Reference fix restarts recommendation: the leaked memory stays in the running process until it "
        "restarts."],
    "dns-error-005": [
        "kill_pods_after: cart keeps a long-lived connection to valkey-cart; a routine reschedule of the "
        "valkey pod forces it to look the name up again."],
    "k8s-oom-cascade-001": [
        "The cart is a native-compiled .NET binary that needs only a few MiB. Measured on this cluster: at "
        "5-20Mi it starts and is only OOM-killed after 6-15 minutes of traffic growth; at 3Mi the container is "
        "OOM-killed while starting, every time (\"container init was OOM-killed (memory limit too low?)\").",
        "strategy Recreate: single-replica service, so the old healthy pod is gone."],
    "wl-dns-policy-none-029": [
        "Recreate: checkout's init container also needs DNS, so a rolling update would leave the old pod "
        "serving and never cause an outage."],
    "wl-jvm-heap-over-limit-031": [
        "Measured: at 300Mi the JVM runs for minutes (heap pages are only touched as used), at 200Mi it OOMs "
        "twice then settles, at 150Mi it crash-loops with OOMKilled."],
    "net-bandwidth-053": [
        "tc units: \"kbps\" = kilobytes per second. At 8kbps images took ~2.6s (vs ~0.2s)."],
    "dns-random-057": [
        "DNSChaos needs a shell in the target container; recommendation (python) has one."],
    "jvm-exception-062": [
        "Byteman can only throw checked exceptions a method declares; getAds declares none."],
    "flag-ad-failure-064": [
        "adFailure fails ~1 in 10 requests: 30 probes catch it ~96% of the time."],
    "flag-ad-manual-gc-066": [
        "The JVM can stay wedged after the flag is off (run 5: ads still timing out 5 min later), so both "
        "the fix and the revert restart it."],
    "obs-pii-redaction-removed-069": [
        "Background: the services emit raw personal data in span attributes (emitRawPii). The actual "
        "incident: the collector pipeline no longer scrubs it."],
    "valkey-maxmemory-075": [
        "256kb is below even an empty instance's footprint, so every write is refused."],
    "grafana-datasource-089": [
        "No restarts: the grafana-sc-datasources sidecar watches ConfigMaps labelled grafana_datasource and "
        "calls Grafana's provisioning reload API, so edits apply live (~15s)."],
    "hard-cart-chained-addr-auth-103": [
        "recreate_pods: old cart pods hold connections authenticated before the rotation and would keep "
        "working; replacing them makes every cart connection new (as 076 does with a restart)."],
}

FAULT_LEVEL = ("restart_on_revert", "revert_hooks")
KNOWN_META = {"family", "mechanism", "title", "est_pass_rate", "split", "generated", "tier", "layers",
              "difficulty_drivers", "noise", "realistic_pattern", "built_from", "prompt_easier", "golden",
              "note", "notes"}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def v2_step(step):
    step = dict(step)
    t = step.pop("type")
    if t == "composite":
        raise ValueError("nested composite faults are not supported")
    return {"mechanism": ALIASES[t], **step}


def v2_fault(fault):
    fault = dict(fault)
    if fault["type"] == "composite":
        top = {k: fault.pop(k) for k in FAULT_LEVEL if k in fault}
        extra = set(fault) - {"type", "steps"}
        if extra:
            raise ValueError(f"unexpected keys on a composite fault: {extra}")
        steps = [v2_step(s) for s in fault["steps"]]
    else:
        top = {k: fault.pop(k) for k in FAULT_LEVEL if k in fault}
        if "pause_s" in fault:
            raise ValueError("pause_s on a single-step fault was ignored by v1; remove it first")
        steps = [v2_step(fault)]
    return {"steps": steps, **top}


def injector(steps):
    kinds = set()
    for s in steps:
        if s.get("noise"):
            continue
        m = s["mechanism"]
        kinds.add("chaos-mesh" if m.startswith("chaos.") else "flagd" if m.startswith("app.flag")
                  else "exec" if m.startswith("runtime.") else "k8s-api")
    return kinds.pop() if len(kinds) == 1 else "mixed"


def to_template(v1, ref):
    meta = v1.get("meta") or {}
    unknown = set(meta) - KNOWN_META
    if unknown:
        raise ValueError(f"{v1['id']}: unknown meta keys {unknown}")
    if v1["task"].get("mode") != "diagnose_and_mitigate":
        raise ValueError(f"{v1['id']}: unexpected task.mode {v1['task'].get('mode')}")
    if v1.get("stack") != {"cluster": "kind-ai-gym", "apps": ["otel-demo"],
                           "observability": ["prometheus", "grafana", "jaeger"]}:
        raise ValueError(f"{v1['id']}: unexpected stack {v1.get('stack')}")
    fault = v2_fault(v1["fault"])
    prompts = {"page": v1["task"]["prompt"]}
    if meta.get("prompt_easier"):
        prompts["hinted"] = meta["prompt_easier"]
    tags = {"injector": injector(fault["steps"])}
    if meta.get("difficulty_drivers"):
        tags["drivers"] = list(meta["difficulty_drivers"])
    verifier = {"checks": v1["verifier"]["checks"], "root_cause": v1["verifier"].get("root_cause") or []}
    if v1["verifier"].get("forbidden") != DEFAULTS["forbidden"]:
        verifier["forbidden"] = v1["verifier"]["forbidden"]
    reference = {"commands": v1["solution"]["commands"]}
    if ref:
        reference.update({k: v for k, v in ref.items() if v})
    notes = list(NOTES.get(v1["id"], []))
    for key in ("note", "notes"):
        if meta.get(key):
            notes += meta[key] if isinstance(meta[key], list) else [meta[key]]
    t = {"spec_version": 2, "id": v1["id"], "version": 1, "title": meta["title"], "mechanism": meta["mechanism"],
         "family": meta["family"], "split": meta.get("split", "train"), "seed": v1["seed"], "world": "k8s-shop",
         "bench_eligible": not any(s["mechanism"] == "chaos.mesh" for s in fault["steps"])}
    if v1.get("tools") != DEFAULTS["tools"]:
        t["tools"] = v1["tools"]
    t.update({"task": {"kind": "incident", "prompts": prompts}, "tags": tags, "fault": fault,
              "verifier": verifier, "reference": reference})
    if v1.get("validation"):
        t["validation"] = v1["validation"]
    if v1.get("budget") != DEFAULTS["budget"]:
        t["budget"] = v1["budget"]
    if notes:
        t["notes"] = notes
    info = {k: meta[k] for k in ("golden", "tier", "layers", "realistic_pattern", "built_from") if k in meta}
    if info:
        t["meta"] = info
    Template.model_validate(t)
    return t


def main():
    catalog = {e["id"]: e for e in load_module(REPO / "gym" / "catalog.py", "v1_catalog").CATALOG}
    hard = {e["id"]: e for e in load_module(REPO / "scripts" / "build_hard_scenarios.py", "v1_hard").H}
    defaults = generate.load_defaults()
    plans = []
    for spec_path in sorted(SCEN.glob("*/spec.yaml")):
        v1 = yaml.safe_load(spec_path.read_text())
        sid, sdir = v1["id"], spec_path.parent
        golden = (v1.get("meta") or {}).get("golden", False)
        if sid in catalog:
            e = catalog[sid]
            ref = {"cause": e["cause"], "diagnose": e["diagnose"]}
        elif sid in hard:
            e = hard[sid]
            ref = {"cause": e["cause"], "diagnose": e["diagnose"], "traps": e["traps"], "noise": e["noise_desc"]}
        elif golden:
            ref = None
        else:
            raise ValueError(f"{sid}: not golden and not found in catalog.py or build_hard_scenarios.py")
        t = to_template(v1, ref)
        extra = [p for p in sdir.iterdir() if p.name not in ("spec.yaml", "reference_solution.md")]
        if not golden:
            files = {p.name: p.read_text() for p in extra}
            md = generate.reference_markdown(generate.resolve(t, defaults, files))
            if md != (sdir / "reference_solution.md").read_text():
                raise ValueError(f"{sid}: generated reference_solution.md would differ from today's")
        plans.append((t, sdir, extra, golden))
    for t, sdir, extra, golden in plans:
        tdir = REPO / "templates" / t["family"] / t["id"]
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "template.yaml").write_text(generate.dump(t))
        for p in extra:
            shutil.copy2(p, tdir / p.name)
        if golden:
            shutil.copy2(sdir / "reference_solution.md", tdir / "reference_solution.md")
    print(f"wrote {len(plans)} templates "
          f"({sum(1 for p in plans if p[3])} with hand-written reference solutions)")


if __name__ == "__main__":
    main()
