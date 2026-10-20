#!/usr/bin/env python3
"""One suite's results as JSON, for the web app (and anything else that shows them): the leaderboard, the scoreboard,
pass rates by tag, the calibration bands (fix mode) and the suite's catalog. Every number comes from the same code as
the markdown reports (leaderboard.py, scoreboard.py, calibration.py, rows.py), so the web app never recomputes a
result.

  python bench/export.py --suite bench-v1-dev                    JSON on stdout
  python bench/export.py --suite hard-v1 --mode diagnose --out hard-v1-diagnose.json

The catalog has every member's title, tags, prompt at the suite's hint level, validation status and oracle result.
Whether a page may show a prompt or a transcript is the web app's decision (private suites and Hard stay private).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import calibration  # noqa: E402
import leaderboard  # noqa: E402
import rows as R  # noqa: E402
import scoreboard  # noqa: E402
from gym import harness  # noqa: E402
from gym.core import status, suites  # noqa: E402
from gym.spec import prompt_of, tier_of  # noqa: E402

SCHEMA = 1   # bump when a field changes meaning or goes away (adding fields does not need it)


def _r(x, n=3):
    return None if x is None else round(x, n)


def leaderboard_part(latest):
    return [{"model": s["model"], "episodes": s["n"], "passed": s["k"], "pass_rate": _r(s["p"]),
             "ci95": [_r(s["lo"]), _r(s["hi"])], "clean": s["clean"], "collateral": s["touched"],
             "made_worse": s["worse"], "forbidden": s["forbidden"], "avg_commands": _r(s["steps"], 1),
             "avg_tokens": round(s["tokens"]), "errors_invalid": s["skipped"]}
            for s in leaderboard.model_stats(latest)]


def scoreboard_part(finished, grade):
    out = []
    for t in scoreboard.score_table(finished, grade, scoreboard.prices()):
        n, judged = t["Episodes"], t["_judged"]
        out.append({"model": t["Model"], "episodes": n, "mitigated": t["_mit"], "mitigation_rate": _r(t["_mit"] / n),
                    "judged": judged, "diagnosis_correct": t["_diag"] if judged else None,
                    "e2e": t["_e2e"] if judged else None, "clean": t["_clean"], "made_worse": t["_worse"],
                    "ttd_s": _r(t["_ttd"], 1), "ttm_s": _r(t["_ttm"], 1), "avg_tokens": _r(t["_tokens"], 0),
                    "cost_usd": _r(t["_cost"], 4),
                    "cost_per_solved_usd": _r(t["_cost"] / t["_mit"], 4) if t["_cost"] is not None and t["_mit"]
                    else None})
    return out


def oracle_part(suite, mode):
    """Latest oracle episode of each member's exact instance in this mode: (ok, problems), or None if never run."""
    import agent_bench
    latest = {}
    for r in R.latest(R.read_jsonl(R.RESULTS / agent_bench.ORACLE / "results.jsonl")):
        if R.mode(r) == mode:
            latest[(r["scenario"], r.get("content_hash"))] = r
    out = {}
    for m in suite.instances:
        r = latest.get((m.id, m.hash))
        out[m.id] = None if r is None else agent_bench.oracle_problems(r)
    return out


def catalog_part(suite, mode):
    insts, records = suites.instances(), status.load_records()
    oracle = oracle_part(suite, mode)
    out = []
    for m in suite.instances:
        spec = insts.get(m.id, (None,))[0]
        if spec is None or spec["content_hash"] != m.hash:
            out.append({"id": m.id, "hash": m.hash, "current": False})
            continue
        st = status.of_spec(spec, records)
        problems = oracle[m.id]
        out.append({"id": m.id, "hash": m.hash, "current": True, "title": spec.get("title"), "tier": tier_of(spec),
                    "task_kind": spec["task"].get("kind", "incident"), "tags": spec["tags"],
                    "prompt": prompt_of(spec, suite.hint_level), "max_steps": (spec.get("budget") or {}).get("max_steps"),
                    "validation": {"status": st.status, "runs": st.runs, "failures": st.failures,
                                   "long_holds": st.long_holds, "summary": st.summary()},
                    "oracle": None if problems is None else ("ok" if not problems else "problem"),
                    "oracle_problems": problems or []})
    return out


def build(suite, mode="fix", judge=None):
    latest = R.load(suite, run_mode=mode)
    finished = [r for r in latest if r.get("status") not in ("error", "invalid")]
    res_dir = R.results_dir(suite)
    judge, grade = scoreboard.judge_grades(R.read_jsonl(res_dir / "judgments.jsonl"), finished, judge)
    sha, dirty = harness.git_state(exclude=("results", "bench/results"))
    return {
        "schema": SCHEMA, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": {"git_sha": sha, "git_dirty": dirty, "prompt_version": R.PROMPT_VERSION},
        "suite": {"name": suite.name, "version": suite.version, "visibility": suite.visibility,
                  "hint_level": suite.hint_level, "fingerprint": suites.fingerprint(suite),
                  "instances": len(suite.instances)},
        "mode": mode, "judge": judge,
        "episodes": len(latest), "models": sorted({r["model"] for r in latest}),
        "leaderboard": leaderboard_part(latest) if latest else [],
        "scoreboard": scoreboard_part(finished, grade) if finished else [],
        "breakdowns": R.axis_counts(latest),
        "calibration": calibration.build(suite, judge) if mode == "fix" and latest else None,
        "catalog": catalog_part(suite, mode),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", required=True, help="suite name (bench-v1-dev) or path")
    ap.add_argument("--mode", choices=("fix", "diagnose", "detect"), default="fix")
    ap.add_argument("--judge", help="whose diagnosis grades to use (default: the one that graded most episodes)")
    ap.add_argument("--out", help="write the JSON here instead of stdout")
    a = ap.parse_args()
    suite = R.suite_from_args(argparse.Namespace(suite=a.suite, any_version=False))
    text = json.dumps(build(suite, a.mode, a.judge), indent=1) + "\n"
    if a.out:
        Path(a.out).write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
