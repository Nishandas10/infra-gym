#!/usr/bin/env python3
"""The headline table, in the same shape as SREGym's leaderboard, plus Infra Gym's own safety and cost columns.

  python bench/scoreboard.py --suite hard-v1
  python bench/scoreboard.py --suite bench-v1-dev --judge claude-opus-5-5
  python bench/scoreboard.py --suite hard-v1 --common     only scenarios every model finished

Columns
  Diag. (%)   root cause stated correctly in the model's report (graded by bench/judge.py; partial = not correct)
  Mit. (%)    verifier PASS: the service works again and stays working (no LLM involved)
  E2E (%)     both in the same episode: correct root cause AND verifier PASS
  TTD (s)     mean seconds from the agent's start to its first command that changed the cluster
  TTM (s)     mean seconds from the agent's start to the verifier seeing the service working (PASS episodes only)
  Tokens      mean input + output tokens per episode
  Clean (%)   PASS with no collateral change, no damage and no forbidden action
  Worse       episodes where the agent broke something that still worked during the incident
  $/solved    API cost divided by PASS episodes (prices from config.yaml)
Below the table, Mit. (%) by the tag axes layer, fix type and drivers.
Writes scoreboard-<suite>.md and .csv next to the results (bench/results, or private/results for a private suite)
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rows as R  # noqa: E402
from rows import ep_key, read_jsonl  # noqa: E402


def prices():
    for name in ("config.yaml", "config.full.yaml"):
        p = HERE / name
        if p.exists():
            cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return {m["id"]: m.get("price") for m in cfg.get("models", [])}
    return {}


def cost(r, p):
    """The episode's dollars: what the provider billed (OpenRouter) if recorded, else its tokens at price `p` (from
    config.yaml; the price the row recorded when config.yaml does not list the model, e.g. one added in the web app)."""
    return R.cost_usd(r, p or r.get("price"))


def judge_grades(judgments, rows, judge=None):
    """(judge, {episode key: root-cause grade}): the given judge, else the one that graded most of these rows."""
    if not judge:
        keys = {ep_key(r) for r in rows}
        used = Counter(j["judge"] for j in judgments if j["key"] in keys)
        judge = used.most_common(1)[0][0] if used else None
    grade = {}
    for j in judgments:
        if j["judge"] == judge:
            grade[j["key"]] = j["root_cause"]  # later lines win
    return judge, grade


def score_table(rows, grade, pr):
    """One entry per model, best Mit. first (also used by bench/export.py). Keys starting with _ are raw counts."""
    by = defaultdict(list)
    for r in rows:
        by[r["model"]].append(r)
    table = []
    for m, rs in by.items():
        n = len(rs)
        judged = [r for r in rs if ep_key(r) in grade]
        diag = sum(grade[ep_key(r)] == "correct" for r in judged)
        e2e = sum(bool(r.get("passed")) and grade[ep_key(r)] == "correct" for r in judged)
        mit = sum(bool(r.get("passed")) for r in rs)
        costs = [cost(r, pr.get(m)) for r in rs]
        total = sum(c for c in costs if c is not None) if any(c is not None for c in costs) else None
        table.append({
            "Model": m, "Episodes": n,
            "Diag. (%)": pct(diag, len(judged)) if judged else "not judged",
            "Mit. (%)": pct(mit, n),
            "E2E (%)": pct(e2e, len(judged)) if judged else "not judged",
            "TTD (s)": "-" if mean(r.get("ttd_s") for r in rs) is None else f"{mean(r.get('ttd_s') for r in rs):.0f}",
            "TTM (s)": "-" if mean(r.get("ttm_s") for r in rs if r.get("passed")) is None
                       else f"{mean(r.get('ttm_s') for r in rs if r.get('passed')):.0f}",
            "Tokens": fmt_tokens(mean((r.get("tokens_in", 0) or 0) + (r.get("tokens_out", 0) or 0) for r in rs)),
            "Clean (%)": pct(sum(bool(r.get("clean")) for r in rs), n),
            "Worse": str(sum(bool(r.get("made_worse")) for r in rs)),
            "$/solved": "-" if total is None or not mit else f"{total / mit:.2f}",
            "_judged": len(judged), "_mit": mit, "_diag": diag, "_e2e": e2e, "_cost": total,
            "_clean": sum(bool(r.get("clean")) for r in rs), "_worse": sum(bool(r.get("made_worse")) for r in rs),
            "_ttd": mean(r.get("ttd_s") for r in rs), "_ttm": mean(r.get("ttm_s") for r in rs if r.get("passed")),
            "_tokens": mean((r.get("tokens_in", 0) or 0) + (r.get("tokens_out", 0) or 0) for r in rs),
            "_timed": sum(r.get("agent_s") is not None for r in rs),  # rows from the timing-aware runner
        })
    table.sort(key=lambda t: (-t["_mit"] / t["Episodes"], t["Model"]))
    return table


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt_tokens(n):
    if n is None:
        return "-"
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}K"


def pct(k, n):
    return "-" if not n else f"{100 * k / n:.1f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    R.add_suite_args(ap)
    ap.add_argument("--model", help="only models whose id contains this text")
    ap.add_argument("--judge", help="which judge's grades to use (default: the one with the most grades)")
    ap.add_argument("--common", action="store_true", help="only scenarios that every model finished")
    a = ap.parse_args()
    suite = R.suite_from_args(a)
    res_dir = R.results_dir(suite)

    rows, excluded = [], Counter()
    for r in R.load(suite, a.any_version, a.mode):
        if a.model and a.model not in str(r.get("model")):
            continue
        if r.get("status") in ("error", "invalid"):
            excluded[r.get("status")] += 1
            continue
        rows.append(r)
    if not rows:
        sys.exit("No finished episodes for this selection.")
    if a.common:
        per_model = defaultdict(set)
        for r in rows:
            per_model[r["model"]].add(r["scenario"])
        common = set.intersection(*per_model.values())
        rows = [r for r in rows if r["scenario"] in common]

    judgments = read_jsonl(res_dir / "judgments.jsonl")
    a.judge, grade = judge_grades(judgments, rows, a.judge)
    table = score_table(rows, grade, prices())

    cols = ["Model", "Episodes", "Diag. (%)", "Mit. (%)", "E2E (%)", "TTD (s)", "TTM (s)", "Tokens",
            "Clean (%)", "Worse", "$/solved"]
    title = R.title(suite, a.any_version, a.mode)
    L = [f"# Infra Gym scoreboard ({title})\n", *R.provenance(suite, rows, a.any_version), "",
         "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for t in table:
        L.append("| " + " | ".join(str(t[c]) for c in cols) + " |")
    L.append("")
    L.append(f"Diagnosis judge: {a.judge or 'none yet (run bench/judge.py)'}. Mitigation is the verifier's PASS, "
             "with no LLM involved.")
    for t in table:
        notes = []
        if isinstance(t["_judged"], int) and t["_judged"] < t["Episodes"]:
            notes.append(f"{t['Episodes'] - t['_judged']} episode(s) not judged yet (Diag./E2E use judged ones only)")
        if t["_timed"] < t["Episodes"]:
            notes.append(f"{t['Episodes'] - t['_timed']} episode(s) ran before timing was recorded (no TTD/TTM)")
        if notes:
            L.append(f"- {t['Model']}: " + "; ".join(notes))
    if excluded:
        L.append(f"Excluded (API error / invalid): {dict(excluded)}")
    L.append("TTD and TTM include the model's own thinking and API time, so faster providers score better.")
    L += R.axis_tables(rows, [t["Model"] for t in table], counted=lambda r: True, what="Mit. (%)")
    text = "\n".join(L)
    print(text)
    out = res_dir / f"scoreboard-{title}.md"
    out.write_text(text + "\n", encoding="utf-8")
    with open(res_dir / f"scoreboard-{title}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(table)
    print(f"\n(saved to {out} and scoreboard-{title}.csv)")


if __name__ == "__main__":
    main()
