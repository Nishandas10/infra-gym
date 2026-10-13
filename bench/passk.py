#!/usr/bin/env python3
"""Per-scenario table for multi-attempt runs: pass@1 (average attempt), pass@k (solved in any attempt),
and an estimated bill from the token counts.
Usage: python bench/passk.py [--suite bench-v1-dev] [--in-price 0.75 --out-price 3.75]"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rows as R  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--in-price", type=float, default=0.75, help="$ per 1M input tokens")
ap.add_argument("--out-price", type=float, default=3.75, help="$ per 1M output tokens (thinking included)")
ap.add_argument("--model", default="")
R.add_suite_args(ap)
a = ap.parse_args()

latest = R.load(R.suite_from_args(a), a.any_version)
if not latest:
    sys.exit("No results yet.")

by = defaultdict(lambda: defaultdict(list))
for r in latest:
    if a.model in r["model"]:
        by[r["model"]][r["key"]].append(r)

for model, scs in by.items():
    print(f"\n## {model}\n")
    print("| Scenario | Attempts | Passed | Solved in any attempt | Stop reasons | Avg commands | Avg minutes |")
    print("|---|---|---|---|---|---|---|")
    tot_att = tot_pass = any_pass = valid_sc = 0
    tin = tout = 0
    for sid in sorted(scs):
        rs = sorted(scs[sid], key=lambda r: r["attempt"])
        done = [r for r in rs if r.get("status") == "done"]
        passed = sum(bool(r["passed"]) for r in done)
        tot_att += len(done)
        tot_pass += passed
        if done:
            valid_sc += 1
            any_pass += passed > 0
        tin += sum(r.get("tokens_in", 0) for r in rs)
        tout += sum(r.get("tokens_out", 0) for r in rs)
        stops = ",".join(("PASS" if r["passed"] else (r.get("stop") or "fail")) if r.get("status") == "done"
                         else r.get("status", "?") for r in rs)
        cmds = sum(r.get("steps", 0) for r in done) / len(done) if done else 0
        mins = sum(r.get("minutes", 0) for r in done) / len(done) if done else 0
        print(f"| {sid} | {len(rs)} | {passed}/{len(done)} | {'YES' if passed else 'no'} | {stops} | {cmds:.0f} | {mins:.1f} |")
    if tot_att:
        print(f"\n**pass@1 (average of single attempts): {tot_pass}/{tot_att} = {100*tot_pass/tot_att:.0f}%**")
    if valid_sc:
        print(f"**pass@{max(len(v) for v in scs.values())} (solved in any attempt): {any_pass}/{valid_sc} scenarios = {100*any_pass/valid_sc:.0f}%**")
    cost = tin / 1e6 * a.in_price + tout / 1e6 * a.out_price
    print(f"Tokens: {tin:,} in / {tout:,} out  ->  about ${cost:.2f} at ${a.in_price}/${a.out_price} per 1M "
          f"(estimate; check your Google AI Studio billing page for the real number)")
