"""Generate scenario folders from gym/catalog.py and write scenarios/CATALOG.md.

usage:
  python scripts/generate_scenarios.py            # write/refresh generated scenarios + index
  python scripts/generate_scenarios.py --index    # only rebuild scenarios/CATALOG.md

Uniqueness is enforced: every scenario id and every mechanism key (the
root-cause class) must be unique across the golden and generated scenarios.
"""
import argparse
import json
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from gym import checks  # noqa: E402
from gym.catalog import CATALOG  # noqa: E402

SCEN = REPO / "scenarios"
FORBIDDEN = ["delete_namespace", "disable_alerts", "edit_verifier", "delete_the_verifier_probe"]


class Dumper(yaml.SafeDumper):
    pass


def _str(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


Dumper.add_representer(str, _str)


def spec_for(e):
    seed = int(re.search(r"(\d+)$", e["id"]).group(1)) + 1000
    return {
        "id": e["id"],
        "seed": seed,
        "stack": {"cluster": "kind-ai-gym", "apps": ["otel-demo"], "observability": ["prometheus", "grafana", "jaeger"]},
        "fault": e["fault"],
        "task": {"mode": "diagnose_and_mitigate", "prompt": e["prompt"]},
        "tools": ["kubectl", "helm", "curl"],
        "verifier": {
            "outcome": [checks.describe(c) for c in e["checks"]],
            "root_cause": e["root"],
            "forbidden": FORBIDDEN,
            "checks": e["checks"],
        },
        "solution": {"commands": e["solution"]},
        "validation": e["validation"],
        "budget": {"max_steps": 30, "wall_s": 900},
        "meta": {"family": e["family"], "mechanism": e["mechanism"], "title": e["title"], "generated": True,
                 "est_pass_rate": None, "split": "train", **({"notes": e["notes"]} if e.get("notes") else {})},
    }


def reference_for(e):
    lines = [f"# Reference solution: {e['id']}", "", f"**{e['title']}**", "",
             f"**Root cause:** {e['cause']}", "", "## How to find it", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(e["diagnose"], 1)]
    lines += ["", "## Fix", "", "```bash", *e["solution"], "```", "", "## Confirm", "",
              f"`python verifiers/verify.py scenarios/{e['id']}` passes.", ""]
    return "\n".join(lines)


def load_all_specs():
    out = []
    for p in sorted(SCEN.glob("*/spec.yaml")):
        out.append(yaml.safe_load(p.read_text()))
    return out


def latest_records():
    path = REPO / "results" / "validation.jsonl"
    recs = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            recs[rec["id"]] = rec
    return recs


def latest_verdicts():
    return {k: v["verdict"] for k, v in latest_records().items()}


def write_index():
    specs = load_all_specs()
    verdicts = latest_verdicts()
    mechs = {}
    for s in specs:
        m = (s.get("meta") or {}).get("mechanism", "?")
        mechs.setdefault(m, []).append(s["id"])
    dups = {m: ids for m, ids in mechs.items() if len(ids) > 1}
    if dups:
        sys.exit(f"duplicate mechanism keys (not unique scenarios): {dups}")
    families = {}
    for s in specs:
        families.setdefault((s.get("meta") or {}).get("family", "?"), []).append(s)
    validated = sum(1 for s in specs if verdicts.get(s["id"]) == "VALIDATED")
    recs = latest_records()
    summary = ["| family | scenarios | validated | median detect | median recover |", "|---|---|---|---|---|"]
    for fam in sorted(families):
        ids = [s["id"] for s in families[fam]]
        ok = [recs[i] for i in ids if i in recs and recs[i]["verdict"] == "VALIDATED"]

        def med(key):
            vals = sorted(r["timings"][key] for r in ok if key in r["timings"])
            return f"{vals[len(vals) // 2]}s" if vals else "-"
        summary.append(f"| {fam} | {len(ids)} | {len(ok)} | {med('detect_s')} | {med('recover_s')} |")
    lines = ["# Scenario catalog", "",
             f"{len(specs)} scenarios, each a distinct root-cause mechanism "
             f"({validated} validated end to end on the live cluster).", "",
             *summary, "",
             "Detect = time from injection until the verifier fails; recover = time from running the reference "
             "solution until it passes again.", "",
             "Uniqueness rule: a scenario counts only if its root-cause mechanism differs from every other one. "
             "Changing only numbers (memory size, latency, percentages), names or random seeds makes a variant, "
             "not a new scenario, so variants are not listed here.", "",
             "Validation = baseline healthy -> inject -> verifier FAIL -> still FAIL for a do-nothing agent "
             "-> reference solution -> verifier PASS -> exact restore (see `scripts/validate_scenario.py`).", "",
             "| id | family | mechanism | title | validation |", "|---|---|---|---|---|"]
    for fam in sorted(families):
        for s in sorted(families[fam], key=lambda x: x["id"]):
            meta = s.get("meta") or {}
            title = meta.get("title") or s["task"]["prompt"][:60]
            lines.append(f"| `{s['id']}` | {fam} | `{meta.get('mechanism', '?')}` | {title} | "
                         f"{verdicts.get(s['id'], 'not run')} |")
    lines.append("")
    (SCEN / "CATALOG.md").write_text("\n".join(lines))
    print(f"wrote scenarios/CATALOG.md ({len(specs)} scenarios, {validated} validated)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", action="store_true")
    args = p.parse_args()
    if not args.index:
        ids = [e["id"] for e in CATALOG]
        assert len(ids) == len(set(ids)), "duplicate ids in catalog"
        for e in CATALOG:
            d = SCEN / e["id"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "spec.yaml").write_text(yaml.dump(spec_for(e), Dumper=Dumper, sort_keys=False, width=110,
                                                   allow_unicode=True))
            (d / "reference_solution.md").write_text(reference_for(e))
        print(f"generated {len(CATALOG)} scenarios")
    write_index()


if __name__ == "__main__":
    main()
