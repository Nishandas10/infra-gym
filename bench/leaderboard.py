#!/usr/bin/env python3
"""Turns the benchmark results into a leaderboard (printed, and saved as leaderboard-<suite>.md).

  python bench/leaderboard.py --suite bench-v1-dev            only rows of exactly the suite's instances
  python bench/leaderboard.py --suite bench-v1-dev --common   only scenarios every model finished
  python bench/leaderboard.py                                 every recorded episode (versions may differ)

Pass rates are broken down by the tag axes layer, fix type and drivers. Private suites read and write
the private checkout's results (bench/rows.py).
"""
import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rows as R  # noqa: E402


def wilson(k, n, z=1.96):
    """Pass rate plus a 95% range that stays honest for small numbers of episodes."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def common_only(latest):
    """Only the scenarios every model has a finished result for; returns (rows, number of such scenarios, models)."""
    models_all = {r["model"] for r in latest}
    have = defaultdict(set)
    for r in latest:
        if r.get("status") == "done":
            have[r["scenario"]].add(r["model"])
    shared = {k for k, ms in have.items() if ms == models_all}
    return [r for r in latest if r["scenario"] in shared], len(shared), len(models_all)


def model_stats(latest):
    """One entry per model, best pass rate first (also used by bench/export.py)."""
    by_model = defaultdict(list)
    for r in latest:
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
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    R.add_suite_args(ap)
    ap.add_argument("--common", action="store_true",
                    help="only scenarios that every model has a finished result for (fair comparison)")
    ap.add_argument("--model", default="", help="only models whose ID contains one of these (comma-separated)")
    args = ap.parse_args()
    suite = R.suite_from_args(args)
    latest = R.load(suite, args.any_version, args.mode)
    if args.model:
        wanted = [w.strip() for w in args.model.split(",") if w.strip()]
        latest = [r for r in latest if any(w in r["model"] for w in wanted)]
    notes = []
    if args.common:
        latest, shared, models_all = common_only(latest)
        notes.append(f"Compared on the {shared} scenarios that all {models_all} models finished.")
    if not latest:
        sys.exit("Nothing to show with these filters." + ("" if suite else " Run: python bench/agent_bench.py run"))
    stats = model_stats(latest)

    name = R.title(suite, args.any_version, args.mode)
    out = [f"# Leaderboard ({name})", "", *R.provenance(suite, latest, args.any_version), *notes, "",
           "| Rank | Model | Pass rate | 95% range | Passed / episodes | Clean fixes | Collateral changes | "
           "Made it worse | Forbidden | Avg commands | Avg tokens | Errors/invalid |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, s in enumerate(stats, 1):
        out.append(f"| {i} | {s['model']} | {s['p']*100:.1f}% | {s['lo']*100:.1f}–{s['hi']*100:.1f}% | "
                   f"{s['k']}/{s['n']} | {s['clean']}/{s['n']} | {s['touched']} | {s['worse']} | {s['forbidden']} | "
                   f"{s['steps']:.1f} | {s['tokens']:,.0f} | {s['skipped']} |")
    out += R.axis_tables(latest, [s["model"] for s in stats])
    out += ["", "Errors/invalid = API failures, or the scenario's baseline/fault check misbehaved; excluded from "
            "the pass rate. Clean fixes = passed with no collateral change, nothing made worse and no forbidden "
            "action. Collateral = changed/created/deleted objects unrelated to the fault (incl. noise objects); "
            "made it worse = a shop check that passed during the fault failed after the agent."]

    text = "\n".join(out)
    print(text)
    out_file = R.results_dir(suite) / f"leaderboard-{name}.md"
    out_file.write_text(text + "\n")
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
