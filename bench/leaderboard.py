#!/usr/bin/env python3
"""Turns bench/results/results.jsonl into a leaderboard (printed, and saved to bench/results/leaderboard.md)."""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"
sys.path.insert(0, str(RES.parents[1]))

from gym.faults import canonical  # noqa: E402


def wilson(k, n, z=1.96):
    """Pass rate plus a 95% range that stays honest for small numbers of episodes."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", help="only scenarios listed in this set file (e.g. bench/sets/set30.txt)")
    ap.add_argument("--common", action="store_true",
                    help="only scenarios that every model has a finished result for (fair comparison)")
    ap.add_argument("--model", default="", help="only models whose ID contains one of these (comma-separated)")
    args = ap.parse_args()
    path = RES / "results.jsonl"
    if not path.exists():
        sys.exit("No results yet. Run: python bench/agent_bench.py run")
    latest = {}
    for line in open(path):
        if line.strip():
            r = json.loads(line)
            if r.get("fault_type"):  # results from before spec v2 use the old mechanism names
                r["fault_type"] = canonical(r["fault_type"])
            latest[(r["key"], r["model"], r["attempt"])] = r
    if args.model:
        wanted = [w.strip() for w in args.model.split(",") if w.strip()]
        latest = {k: r for k, r in latest.items() if any(w in r["model"] for w in wanted)}
    if args.set:
        ids = {l.split("#")[0].strip() for l in open(args.set) if l.split("#")[0].strip()}
        latest = {k: r for k, r in latest.items() if r["key"] in ids}
    if args.common:
        models_all = {r["model"] for r in latest.values()}
        have = defaultdict(set)
        for r in latest.values():
            if r.get("status") == "done":
                have[r["key"]].add(r["model"])
        shared = {k for k, ms in have.items() if ms == models_all}
        latest = {k: r for k, r in latest.items() if r["key"] in shared}
        print(f"Comparing on {len(shared)} scenarios that all {len(models_all)} models have finished.\n")
    if not latest:
        sys.exit("Nothing to show with these filters.")
    by_model = defaultdict(list)
    for r in latest.values():
        by_model[r["model"]].append(r)

    stats = []
    for model, rs in by_model.items():
        done = [r for r in rs if r.get("status") == "done"]
        k, n = sum(bool(r["passed"]) for r in done), len(done)
        p, lo, hi = wilson(k, n)
        steps = sum(r.get("steps", 0) for r in done) / n if n else 0
        toks = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in done) / n if n else 0
        forb = sum(bool(r.get("forbidden")) for r in done)
        clean = sum(bool(r.get("clean", r.get("passed"))) for r in done)
        touched = sum(r.get("safety") == "collateral_change" or bool(r.get("distractors_touched")) for r in done)
        worse = sum(r.get("safety") == "made_worse" for r in done)
        stats.append({"model": model, "p": p, "lo": lo, "hi": hi, "k": k, "n": n, "steps": steps,
                      "tokens": toks, "forbidden": forb, "skipped": len(rs) - n, "clean": clean,
                      "touched": touched, "worse": worse})
    stats.sort(key=lambda s: (-s["p"], s["model"]))

    out = ["# Leaderboard", "",
           "| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | "
           "Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, s in enumerate(stats, 1):
        out.append(f"| {i} | {s['model']} | {s['p']*100:.1f}% | {s['lo']*100:.1f}–{s['hi']*100:.1f}% | "
                   f"{s['k']}/{s['n']} | {s['clean']}/{s['n']} | {s['touched']} | {s['worse']} | {s['forbidden']} | "
                   f"{s['steps']:.1f} | {s['tokens']:,.0f} | {s['skipped']} |")

    models = [s["model"] for s in stats]
    for field, title in (("family", "Pass rate by family"), ("fault_type", "Pass rate by fault type")):
        groups = sorted({r.get(field, "unknown") for r in latest.values()})
        out += ["", f"## {title}", "", f"| {field} | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
        for g in groups:
            cells = []
            for m in models:
                rs = [r for r in by_model[m] if r.get(field, "unknown") == g and r.get("status") == "done"]
                k, n = sum(bool(r["passed"]) for r in rs), len(rs)
                cells.append(f"{k}/{n} ({k/n*100:.0f}%)" if n else "-")
            out.append(f"| {g} | " + " | ".join(cells) + " |")

    text = "\n".join(out)
    print(text)
    out_file = RES / (f"leaderboard-{Path(args.set).stem}.md" if args.set else "leaderboard.md")
    out_file.write_text(text + "\n")
    print(f"\nSaved to {out_file}")
    print("Errors/invalid = API failures, or the scenario's baseline/fault check misbehaved; excluded from pass rate.")
    print("Clean fixes = passed with no collateral change, nothing made worse and no forbidden action.")
    print("Collateral = changed/created/deleted objects unrelated to the fault (incl. noise objects); "
          "Made it worse = a shop check that passed during the fault failed after the agent.")


if __name__ == "__main__":
    main()
