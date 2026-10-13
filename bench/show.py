#!/usr/bin/env python3
"""See what the model actually did in an episode.

  python bench/show.py                       list every finished episode
  python bench/show.py --suite bench-v1-dev  ... only those of a suite's instances
  python bench/show.py flag-ad-failure-064   the full story of one episode, step by step
  python bench/show.py flag-ad-failure-064 --full      do not shorten command output
  python bench/show.py flag-ad-failure-064 --out story.md   also save it to a file

Reads results.jsonl and transcripts/<model>/<scenario>__a<N>__<episode>.json in bench/results/
(private/results/ for a private suite).
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rows as R  # noqa: E402



def load_results(suite=None, any_version=False):
    return R.load(suite, any_version)


def short(text, limit):
    text = (text or "").rstrip()
    if limit and len(text) > limit:
        return text[:limit] + f"\n... [{len(text) - limit} more characters, use --full to see all]"
    return text


def indent(text, pad="    "):
    return "\n".join(pad + ln for ln in (text or "").splitlines()) or pad


def list_episodes(rows):
    if not rows:
        print("No finished episodes yet in bench/results/results.jsonl")
        return
    print(f"{'scenario':42} {'model':24} {'try':3} {'result':7} {'safety':18} {'cmds':>4} {'min':>5}")
    for r in sorted(rows, key=lambda r: (r.get("scenario") or "", r.get("model") or "")):
        res = "PASS" if r.get("passed") else (r.get("status") or "FAIL").upper()
        if res == "DONE":
            res = "FAIL"
        print(f"{str(r.get('scenario')):42} {str(r.get('model')):24} {str(r.get('attempt')):3} {res:7} "
              f"{str(r.get('safety') or ''):18} {str(r.get('steps') or 0):>4} {str(r.get('minutes') or ''):>5}")
    print("\nTo read one: python bench/show.py <scenario-name>")


def story(sc_id, model_filter, attempt, full, suite=None, any_version=False):
    limit = 0 if full else 1500
    files = sorted((R.results_dir(suite) / "transcripts").glob(f"*/{sc_id}__a*.json"))
    if model_filter:
        files = [f for f in files if model_filter.replace("/", "__") in f.parent.name]
    if attempt:
        files = [f for f in files if re.search(rf"__a{attempt}(__|\.json)", f.name)]
    if not files:
        sys.exit(f"No transcript found for '{sc_id}'. Run  python bench/show.py  to see the names.")
    rows = load_results(suite, any_version)
    by_episode = {r["episode"]: r for r in rows if r.get("episode")}
    legacy = {(r.get("scenario"), r.get("model"), r.get("attempt")): r for r in rows if not r.get("episode")}
    out = []
    for f in files:
        t = json.loads(f.read_text(encoding="utf-8"))
        r = by_episode.get(t.get("episode")) or legacy.get((t["scenario"], t["model"], t["attempt"]))
        if r is None:
            if suite is not None:   # an episode of another version or hint level than the suite's
                continue
            r = {}
        out.append("=" * 78)
        out.append(f"{t['scenario']}   model: {t['model']}   attempt {t['attempt']}")
        verdict = "PASSED" if t.get("passed") else "DID NOT PASS"
        out.append(f"Result: {verdict}   safety: {r.get('safety')}   commands: {r.get('steps')}   "
                   f"minutes: {r.get('minutes')}   stop reason: {r.get('stop')}")
        if r.get("made_worse"):
            out.append(f"Made worse: {r['made_worse']}")
        if r.get("collateral"):
            out.append(f"Changed unrelated objects: {r['collateral']}")
        if r.get("forbidden"):
            out.append(f"Forbidden actions: {r['forbidden']}")
        out.append(f"Tokens: in {r.get('tokens_in')}  out {r.get('tokens_out')}  "
                   f"cache read {r.get('tokens_cache_read')}  cache write {r.get('tokens_cache_write')}  "
                   f"effort {r.get('effort')}")
        out.append("=" * 78)
        n = 0
        calls = {}
        times = {e.get("step"): e for e in t.get("timeline") or []}
        if t.get("ttd_s") is not None or t.get("ttm_s") is not None:
            out.append(f"Time to first change (TTD): {t.get('ttd_s')}s   time to working service (TTM): {t.get('ttm_s')}s")
        for m in t["messages"]:
            role = m.get("role")
            if role == "system":
                out.append("\n[INSTRUCTIONS GIVEN TO THE MODEL]\n" + indent(short(m.get("content"), limit)))
            elif role == "user":
                out.append("\n[MESSAGE TO THE MODEL]\n" + indent(short(m.get("content"), limit)))
            elif role == "assistant":
                for b in m.get("_blocks") or []:
                    if b.get("type") == "thinking" and (b.get("thinking") or "").strip():
                        out.append("\n[MODEL THINKING]\n" + indent(short(b["thinking"], limit)))
                for p in m.get("_gparts") or []:  # Gemini thought summaries
                    if p.get("thought") and (p.get("text") or "").strip():
                        out.append("\n[MODEL THINKING (summary)]\n" + indent(short(p["text"], limit)))
                if m.get("content"):
                    out.append("\n[MODEL SAYS]\n" + indent(short(m["content"], limit)))
                for c in m.get("tool_calls") or []:
                    n += 1
                    try:
                        cmd = json.loads(c["function"]["arguments"] or "{}").get("command", "")
                    except json.JSONDecodeError:
                        cmd = c["function"]["arguments"]
                    calls[c["id"]] = n
                    e = times.get(n)
                    when = f" at {e['t']:.0f}s" + (", changes the cluster" if e.get("changes") else "") if e else ""
                    out.append(f"\n[COMMAND {n}{when}]\n" + indent(cmd))
            elif role == "tool":
                out.append(f"[OUTPUT of command {calls.get(m.get('tool_call_id'), '?')}]\n"
                           + indent(short(m.get("content"), limit)))
        if r.get("diagnosis"):
            out.append("\n[DIAGNOSIS / FINAL ANSWER]\n" + indent(r["diagnosis"]))
        if t.get("cleanup"):
            out.append("\n[CLEANUP AFTER THE EPISODE]\n" + indent("\n".join(map(str, t["cleanup"]))))
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", nargs="?")
    ap.add_argument("--model")
    ap.add_argument("--attempt")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--out")
    R.add_suite_args(ap)
    a = ap.parse_args()
    suite = R.suite_from_args(a)
    if not a.scenario:
        return list_episodes(load_results(suite, a.any_version))
    text = story(a.scenario, a.model, a.attempt, a.full, suite, a.any_version)
    print(text)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"(saved to {a.out})")


if __name__ == "__main__":
    main()
