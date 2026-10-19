#!/usr/bin/env python3
"""Calibration report: how hard each suite member is for the models measured so far, and whether it separates them.

  python bench/calibration.py --suite bench-v1-dev [--judge claude-sonnet-5-5]

Per model: pass rate over all its episodes with a 95% Wilson interval, and the diagnosis judge's root-cause grades
(bench/judge.py), including "understood, not fixed" and "fixed, cause wrong or not stated".
Per scenario: each model's passes/attempts, the mean of the models' pass rates (every model weighs the same, however
many attempts it ran), a band (easy >= 2/3, hard <= 1/3, else medium; provisional while fewer than MIN_SAMPLES
episodes back it) and the signal: all models pass, all fail, or it separates them.
Counted: finished episodes (status done) of the suite's exact instances at the current prompt version, fix mode.
Output: bench/results/calibration-<suite>.md and .json (private/results/ for a private suite).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rows as R  # noqa: E402

RUBRIC = "v2"
EASY, HARD = 2 / 3, 1 / 3
MIN_SAMPLES = 6   # episodes behind a scenario's band before it is more than provisional


def wilson(k, n, z=1.96):
    """95% Wilson score interval of k successes in n trials, as (low, high); None for n = 0."""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)


def band(rate):
    return "easy" if rate >= EASY else "hard" if rate <= HARD else "medium"


def signal(rates):
    """all_pass / all_fail / separates, from each model's pass rate on one scenario."""
    if all(r == 1 for r in rates):
        return "all_pass"
    if all(r == 0 for r in rates):
        return "all_fail"
    return "separates" if len(set(rates)) > 1 else "same_partial"


def quadrant(passed, grade):
    if grade is None:
        return None
    if passed:
        return "fixed_understood" if grade == "correct" else "fixed_partial" if grade == "partial" else "fixed_cause_wrong"
    return "understood_not_fixed" if grade == "correct" else "not_fixed"


def judgments(judge):
    out = {}
    for j in R.read_jsonl(R.RESULTS / "judgments.jsonl"):
        if j.get("judge") == judge and j.get("rubric") == RUBRIC:
            out[j["key"]] = j   # later lines win
    return out


def build(suite, judge):
    rows = [r for r in R.load(suite) if r.get("status") == "done"]
    grades = judgments(judge)
    models = sorted({r["model"] for r in rows})
    eps = defaultdict(lambda: defaultdict(list))   # scenario -> model -> episodes
    for r in rows:
        j = grades.get(R.ep_key(r))
        grade = j["root_cause"] if j else None
        eps[r["scenario"]][r["model"]].append({
            "attempt": r.get("attempt"), "passed": bool(r.get("passed")), "root_cause": grade,
            "quadrant": quadrant(bool(r.get("passed")), grade), "safety": r.get("safety"),
            "steps": r.get("steps"), "minutes": r.get("minutes")})

    scenarios = []
    for m in suite.instances:
        per = {}
        for model in models:
            es = sorted(eps[m.id].get(model, []), key=lambda e: e["attempt"] or 0)
            if es:
                k = sum(e["passed"] for e in es)
                per[model] = {"k": k, "n": len(es), "rate": round(k / len(es), 3), "episodes": es}
        rates = [p["rate"] for p in per.values()]
        n = sum(p["n"] for p in per.values())
        mean = round(sum(rates) / len(rates), 3) if rates else None
        scenarios.append({
            "id": m.id, "hash": m.hash, "models": per, "episodes": n,
            "model_mean": mean, "band": band(mean) if rates else None, "provisional": n < MIN_SAMPLES,
            "signal": signal(rates) if rates else None,
            "understood_not_fixed": sum(e["quadrant"] == "understood_not_fixed"
                                        for p in per.values() for e in p["episodes"]),
            "fixed_cause_wrong": sum(e["quadrant"] == "fixed_cause_wrong" for p in per.values() for e in p["episodes"])})

    summary = {}
    for model in models:
        es = [e for s in scenarios for e in s["models"].get(model, {}).get("episodes", [])]
        k, n = sum(e["passed"] for e in es), len(es)
        graded = [e for e in es if e["root_cause"]]
        q = defaultdict(int)
        for e in graded:
            q[e["quadrant"]] += 1
        summary[model] = {
            "episodes": n, "passed": k, "pass_rate": round(k / n, 3) if n else None, "wilson95": wilson(k, n),
            "scenarios": sum(1 for s in scenarios if model in s["models"]),
            "graded": len(graded), "root_cause_correct": sum(e["root_cause"] == "correct" for e in graded),
            "quadrants": dict(q)}
    return {"suite": suite.name, "suite_version": suite.version, "prompt_version": R.PROMPT_VERSION,
            "judge": judge, "rubric": RUBRIC, "models": summary, "scenarios": scenarios,
            "bands": {b: sum(s["band"] == b for s in scenarios) for b in ("easy", "medium", "hard")},
            "signals": {g: sum(s["signal"] == g for s in scenarios)
                        for g in ("separates", "all_pass", "all_fail", "same_partial")},
            "not_run": [s["id"] for s in scenarios if not s["models"]]}


def pct(x):
    return "-" if x is None else f"{100 * x:.0f}%"


GRADE_LETTER = {"correct": "C", "partial": "P", "wrong": "W", "missing": "M", None: "?"}


def markdown(cal):
    models = list(cal["models"])
    L = [f"# Calibration: {cal['suite']} v{cal['suite_version']}\n",
         f"Fix mode, prompt v{cal['prompt_version']}, finished episodes only. Diagnosis grades: judge "
         f"`{cal['judge']}`, rubric {cal['rubric']} (C correct, P partial, W wrong, M missing, ? not graded). "
         f"Bands use the mean of the models' pass rates: easy >= 2/3, hard <= 1/3; *provisional* below "
         f"{MIN_SAMPLES} episodes.\n",
         "## Models\n",
         "| Model | Episodes | Pass rate (95% CI) | Root cause correct | Fixed + understood | Understood, not fixed "
         "| Fixed, cause wrong/unstated |",
         "|---|---|---|---|---|---|---|"]
    for model, s in cal["models"].items():
        ci = s["wilson95"]
        q = s["quadrants"]
        L.append(f"| {model} | {s['episodes']} | {s['passed']}/{s['episodes']} ({pct(s['pass_rate'])}; "
                 f"{pct(ci[0])}-{pct(ci[1])}) | {s['root_cause_correct']}/{s['graded']} "
                 f"| {q.get('fixed_understood', 0)} | {q.get('understood_not_fixed', 0)} "
                 f"| {q.get('fixed_cause_wrong', 0)} |")
    b, g = cal["bands"], cal["signals"]
    L += ["", "## Suite\n",
          f"Bands: {b['easy']} easy, {b['medium']} medium, {b['hard']} hard. Signal: {g['separates']} separate the "
          f"models, {g['all_pass']} all pass, {g['all_fail']} all fail"
          + (f", {g['same_partial']} same partial rate" if g["same_partial"] else "") + "."
          + (f" Not run yet: {', '.join(cal['not_run'])}." if cal["not_run"] else "") + "\n",
          "## Scenarios\n",
          "| Scenario | " + " | ".join(models) + " | Mean | Band | Signal | Diagnosis (judge) |",
          "|---|" + "---|" * len(models) + "---|---|---|---|"]
    for s in sorted(cal["scenarios"], key=lambda s: (s["model_mean"] if s["model_mean"] is not None else 2, s["id"])):
        cells = []
        diag = []
        for model in models:
            p = s["models"].get(model)
            cells.append(f"{p['k']}/{p['n']}" if p else "-")
            if p:
                diag.append("".join(GRADE_LETTER[e["root_cause"]] for e in p["episodes"]))
        bnd = "-" if s["band"] is None else s["band"] + (" (provisional)" if s["provisional"] else "")
        L.append(f"| {s['id']} | " + " | ".join(cells) + f" | {pct(s['model_mean'])} | {bnd} "
                 f"| {(s['signal'] or '-').replace('_', ' ')} | {' / '.join(diag) or '-'} |")
    L.append("\nDiagnosis column: one letter per episode in attempt order, models in the column order above.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--judge", default="claude-sonnet-5-5", help="whose diagnosis grades to show (bench/judge.py)")
    a = ap.parse_args()
    suite = R.suite_from_args(argparse.Namespace(suite=a.suite, any_version=False))
    cal = build(suite, a.judge)
    out = R.results_dir(suite)
    (out / f"calibration-{suite.name}.json").write_text(json.dumps(cal, indent=1) + "\n")
    (out / f"calibration-{suite.name}.md").write_text(markdown(cal))
    print(f"wrote {out / f'calibration-{suite.name}.md'} and .json")


if __name__ == "__main__":
    main()
