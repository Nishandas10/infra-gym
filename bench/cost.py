#!/usr/bin/env python3
"""What each model cost, from the tokens recorded in results.jsonl and the prices in config.yaml.

  python bench/cost.py                      cost per model so far
  python bench/cost.py --project 90         ...plus a projection for 90 episodes per model
  python bench/cost.py --model opus         only models whose ID contains this text

Prices are $ per 1M tokens, set per model in config.yaml, e.g.
  price: {input: 4, output: 20, cache_read: 0.20, cache_write: 5}
This is an estimate from the token counts; your provider's billing page has the real number."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--project", type=int, default=0, help="also estimate the cost of this many episodes per model")
ap.add_argument("--model", default="")
a = ap.parse_args()

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
by = defaultdict(list)
for r in latest.values():
    if a.model in r["model"]:
        by[r["model"]].append(r)

print("| Model | Episodes | Input (uncached) | Cache writes | Cache reads | Output | Cost so far | Per episode |"
      + (f" For {a.project} episodes |" if a.project else ""))
print("|---|---|---|---|---|---|---|---|" + ("---|" if a.project else ""))
for model, rs in sorted(by.items()):
    cr = sum(r.get("tokens_cache_read", 0) for r in rs)
    cw = sum(r.get("tokens_cache_write", 0) for r in rs)
    tin = sum(r.get("tokens_in", 0) for r in rs) - cr - cw
    tout = sum(r.get("tokens_out", 0) for r in rs)
    p = prices.get(model)
    if p:
        cost = (tin * p["input"] + cw * p.get("cache_write", p["input"]) + cr * p.get("cache_read", p["input"])
                + tout * p["output"]) / 1e6
        per = cost / len(rs)
        c1, c2 = f"${cost:,.2f}", f"${per:,.2f}"
        c3 = f" ${per * a.project:,.0f} |" if a.project else ""
    else:
        c1 = c2 = "no price in config"
        c3 = " - |" if a.project else ""
    print(f"| {model} | {len(rs)} | {tin:,} | {cw:,} | {cr:,} | {tout:,} | {c1} | {c2} |{c3}")
print("\nEpisodes that ended in an API error still count here (their tokens were billed).")
