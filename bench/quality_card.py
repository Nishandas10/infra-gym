#!/usr/bin/env python3
"""Scenario quality card: how reliable each environment is, from results/validation.jsonl.

  python bench/quality_card.py                 all scenarios
  python bench/quality_card.py --set bench/sets/hard.txt

Per scenario: validation runs, how many reached VALIDATED, flake rate, and the median times to
detect the fault, to recover after the reference fix, and to reset the world afterwards.
Run scripts/validate_scenario.py several times to make the flake rate meaningful."""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ap = argparse.ArgumentParser()
ap.add_argument("--set", help="only scenarios in this set file")
a = ap.parse_args()

path = REPO / "results" / "validation.jsonl"
if not path.exists():
    sys.exit("No results/validation.jsonl yet. Run scripts/validate_scenario.py first.")
runs = defaultdict(list)
for line in open(path):
    try:
        r = json.loads(line)
        runs[r["id"]].append(r)
    except (ValueError, KeyError):
        continue
wanted = None
if a.set:
    wanted = [l.split("#")[0].strip() for l in open(a.set) if l.split("#")[0].strip()]

meta = {}
for p in sorted((REPO / "scenarios").glob("*/spec.yaml")):
    s = yaml.safe_load(p.read_text())
    meta[s["id"]] = s.get("meta") or {}


def med(rs, key):
    vals = [r["timings"][key] for r in rs if key in r.get("timings", {})]
    return f"{statistics.median(vals):.0f}s" if vals else "-"


ids = wanted or sorted(meta)
out = ["| Scenario | Tier | Family | Runs | Validated | Flake rate | Detect | Recover | Reset | Last verdict |",
       "|---|---|---|---|---|---|---|---|---|---|"]
tot_runs = tot_ok = 0
for sid in ids:
    rs = runs.get(sid, [])
    ok = sum(r["verdict"] == "VALIDATED" for r in rs)
    tot_runs += len(rs)
    tot_ok += ok
    flake = f"{100 * (len(rs) - ok) / len(rs):.0f}%" if rs else "-"
    m = meta.get(sid, {})
    out.append(f"| {sid} | {m.get('tier', 'standard')} | {m.get('family', '?')} | {len(rs)} | {ok} | {flake} | "
               f"{med(rs, 'detect_s')} | {med(rs, 'recover_s')} | {med(rs, 'restore_s')} | "
               f"{rs[-1]['verdict'] if rs else 'not run'} |")
out += ["", f"{len(ids)} scenarios, {tot_runs} validation runs, "
            f"{100 * tot_ok / tot_runs:.0f}% of runs VALIDATED" if tot_runs else f"{len(ids)} scenarios, no runs yet"]
text = "\n".join(out)
print(text)
(HERE / "results").mkdir(exist_ok=True)
(HERE / "results" / "quality_card.md").write_text(text + "\n")
print(f"\nSaved to {HERE / 'results' / 'quality_card.md'}")
