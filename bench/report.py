#!/usr/bin/env python3
"""One table for investors and the paper: every model on the Standard and the Hard tier,
with safety and cost. Reads results/results.jsonl, the set files and prices in config.yaml.

  python bench/report.py --standard bench/sets/set30.txt --hard bench/sets/hard.txt
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--standard", default=str(HERE / "sets" / "set30.txt"))
ap.add_argument("--hard", default=str(HERE / "sets" / "hard.txt"))
a = ap.parse_args()


def read_set(p):
    return {l.split("#")[0].strip() for l in open(p) if l.split("#")[0].strip()} if Path(p).exists() else set()


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


def cost(r, price):
    if not price:
        return None
    cr, cw = r.get("tokens_cache_read", 0), r.get("tokens_cache_write", 0)
    unc = r.get("tokens_in", 0) - cr - cw
    return (unc * price["input"] + cw * price.get("cache_write", price["input"]) +
            cr * price.get("cache_read", price["input"]) + r.get("tokens_out", 0) * price["output"]) / 1e6


path = HERE / "results" / "results.jsonl"
if not path.exists():
    sys.exit("No results yet.")
cfg = yaml.safe_load(open(HERE / "config.yaml"))
prices = {m["id"]: m.get("price") for m in cfg.get("models", [])}
latest = {}
for line in open(path):
    if line.strip():
        r = json.loads(line)
        latest[(r["key"], r["model"], r["attempt"])] = r
tiers = {"Standard": read_set(a.standard), "Hard": read_set(a.hard)}
by = defaultdict(lambda: defaultdict(list))
for r in latest.values():
    for tier, ids in tiers.items():
        if r["key"] in ids:
            by[r["model"]][tier].append(r)

rows = []
for model, t in by.items():
    row = {"model": model}
    all_done, spent, solved = [], 0.0, 0
    for tier in tiers:
        done = [r for r in t.get(tier, []) if r.get("status") == "done"]
        k = sum(bool(r.get("passed")) for r in done)
        p, lo, hi = wilson(k, len(done))
        row[tier] = (f"{p*100:.0f}% ({lo*100:.0f}–{hi*100:.0f}), {k}/{len(done)}" if done else "-")
        row[tier + "_p"] = p if done else -1
        all_done += done
        for r in t.get(tier, []):
            c = cost(r, prices.get(model))
            spent += c or 0
        solved += k
    n = len(all_done)
    row["clean"] = f"{sum(bool(r.get('clean')) for r in all_done)}/{n}" if n else "-"
    row["worse"] = sum(r.get("safety") in ("made_worse", "forbidden_action") for r in all_done)
    row["per_ep"] = f"${spent / max(1, sum(len(v) for v in t.values())):.2f}" if prices.get(model) else "no price"
    row["per_solve"] = f"${spent / solved:.2f}" if prices.get(model) and solved else "-"
    rows.append(row)
rows.sort(key=lambda r: (-r["Hard_p"], -r["Standard_p"]))
out = ["| Model | Standard tier | Hard tier | Clean fixes | Made worse / forbidden | Cost per episode | Cost per solved incident |",
       "|---|---|---|---|---|---|---|"]
for r in rows:
    out.append(f"| {r['model']} | {r['Standard']} | {r['Hard']} | {r['clean']} | {r['worse']} | {r['per_ep']} | {r['per_solve']} |")
out += ["", "Pass rates with 95% ranges. Costs are estimates from recorded tokens and config prices."]
text = "\n".join(out)
print(text)
(HERE / "results" / "report.md").write_text(text + "\n")
print(f"\nSaved to {HERE / 'results' / 'report.md'}")
