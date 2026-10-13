#!/usr/bin/env python3
"""One table for investors and the paper: every model on the Standard and the Hard suite, with safety
and cost, then the pass rate by tag axes (layer, fix type, drivers) over both suites.

  python bench/report.py --standard bench-v1-dev --hard hard-v1

Only rows of exactly the suites' instances count (bench/rows.py). Prices come from config.yaml.
"""
import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rows as R  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--standard", default="bench-v1-dev", help="suite for the Standard column")
ap.add_argument("--hard", default="hard-v1", help="suite for the Hard column")
a = ap.parse_args()


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


try:
    tiers = {"Standard": R.suites.load(a.standard), "Hard": R.suites.load(a.hard)}
except (FileNotFoundError, ValueError) as e:
    sys.exit(str(e))
if any(s.visibility == "private" for s in tiers.values()):
    sys.exit("report.py is for published numbers; it does not report private suites")
cfg = yaml.safe_load(open(HERE / "config.yaml"))
prices = {m["id"]: m.get("price") for m in cfg.get("models", [])}
by = defaultdict(lambda: defaultdict(list))
everything = []
for tier, suite in tiers.items():
    for r in R.load(suite):
        by[r["model"]][tier].append(r)
        everything.append(r)
if not everything:
    sys.exit("No results for these suites yet.")

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
st, hd = tiers["Standard"], tiers["Hard"]
out = [f"| Model | Standard ({st.name} v{st.version}) | Hard ({hd.name} v{hd.version}) | Clean fixes | "
       "Made worse / forbidden | Cost per episode | Cost per solved incident |",
       "|---|---|---|---|---|---|---|"]
for r in rows:
    out.append(f"| {r['model']} | {r['Standard']} | {r['Hard']} | {r['clean']} | {r['worse']} | {r['per_ep']} | {r['per_solve']} |")
out += ["", "Pass rates with 95% ranges. Costs are estimates from recorded tokens and config prices."]
for suite in tiers.values():
    out += [f"- {line}" for line in R.provenance(suite, R.load(suite))]
out += R.axis_tables(everything, [r["model"] for r in rows])
text = "\n".join(out)
print(text)
(HERE / "results" / "report.md").write_text(text + "\n")
print(f"\nSaved to {HERE / 'results' / 'report.md'}")
