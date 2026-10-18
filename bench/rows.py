"""Reading benchmark results the same way in every report (leaderboard, scoreboard, report, judge, ...).

An episode is identified by (scenario, model, attempt, content_hash, hint_level, prompt_version):
re-running it replaces the old row (the later line wins), while another scenario version, hint level or
prompt version is a different episode. A suite's reports keep only rows whose (scenario, content_hash)
is a member of the suite, whose hint level is the suite's and whose prompt version is the current one,
so a row counts for every suite that holds exactly the instance it ran and never for a suite that holds
another version of it. Rows from before suites (no content_hash) or from older prompts only show up
with --any-version, which matches members by id alone.

Results of private suites are kept in the private checkout (private/results/), never in
bench/results/, so they cannot be published by accident.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from gym.core import suites  # noqa: E402

RESULTS = HERE / "results"
AXES = ("layer", "fix_type", "drivers")   # tag axes the reports break results down by
# Version of what agent_bench tells the agent (system prompt, reminders, report request).
# 1: until 2026-10-15 (rows without the field). 2: the system prompt states the command budget and the
# agent is reminded when 5 commands are left. 3 (2026-10-17): the system prompt allows that nothing needs fixing
# (false alarms, task.kind false_alarm): "if nothing needs fixing, change nothing and explain why". It also brings the
# diagnose/detect texts (bench/modes.py).
PROMPT_VERSION = 3


def read_jsonl(path):
    rows = []
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def results_dir(suite=None):
    """Where results of this suite live: the private checkout for private suites, else bench/results."""
    if suite is not None and suite.visibility == "private":
        return suites.private_root() / "results"
    return RESULTS


def hint_level(r):
    return r.get("hint_level") or "page"


def prompt_version(r):
    return r.get("prompt_version") or 1


def mode(r):
    """The run mode (bench/modes.py); rows from before modes are fix episodes."""
    return r.get("mode") or "fix"


def cost_usd(r, price):
    """What one episode cost in dollars: what the provider billed (cost_billed_usd, OpenRouter) when recorded, else at
    `price` ($ per 1M tokens: input, output, cache_read, cache_write) from its recorded tokens; None without either.
    tokens_in counts every input token, cached ones included."""
    if r.get("cost_billed_usd") is not None:
        return r["cost_billed_usd"]
    if not price:
        return None
    cr, cw = r.get("tokens_cache_read") or 0, r.get("tokens_cache_write") or 0
    fresh = (r.get("tokens_in") or 0) - cr - cw
    return (fresh * price["input"] + cw * price.get("cache_write", price["input"])
            + cr * price.get("cache_read", price["input"]) + (r.get("tokens_out") or 0) * price["output"]) / 1e6


def identity(r):
    return (r.get("scenario") or r.get("key"), r.get("model"), r.get("attempt"), r.get("content_hash"), hint_level(r),
            prompt_version(r), mode(r))


def ep_key(r):
    """A unique key per episode: its episode id, or scenario|model|attempt for rows from before episode ids."""
    return r.get("episode") or f"{r.get('scenario')}|{r.get('model')}|{r.get('attempt')}"


def latest(rows):
    out = {}
    for r in rows:
        out[identity(r)] = r
    return list(out.values())


def in_suite(rows, suite, any_version=False):
    if any_version:
        ids = {m.id for m in suite.instances}
        return [r for r in rows if r.get("scenario") in ids]
    members = {(m.id, m.hash) for m in suite.instances}
    return [r for r in rows if (r.get("scenario"), r.get("content_hash")) in members
            and hint_level(r) == suite.hint_level and prompt_version(r) == PROMPT_VERSION]


def load(suite=None, any_version=False, run_mode="fix"):
    """The latest row of every episode in one run mode, limited to the suite's members when a suite is given."""
    rows = [r for r in latest(read_jsonl(results_dir(suite) / "results.jsonl")) if mode(r) == run_mode]
    return rows if suite is None else in_suite(rows, suite, any_version)


# ------------------------------------------------------------------ command line
def add_suite_args(ap):
    ap.add_argument("--suite", help="only this suite's instances (name, e.g. bench-v1-dev, or path)")
    ap.add_argument("--set", dest="suite", help="old name of --suite (kept for one release)")
    ap.add_argument("--any-version", action="store_true",
                    help="match suite members by id only, including rows of other scenario versions or hint "
                         "levels (e.g. results from before suites); such numbers are not pinned to the suite")
    ap.add_argument("--mode", choices=("fix", "diagnose", "detect"), default="fix",
                    help="which run mode's episodes to report (bench/modes.py; default fix)")


def suite_from_args(a):
    if not a.suite:
        if getattr(a, "any_version", False):
            sys.exit("--any-version needs --suite")
        return None
    if "--set" in sys.argv:
        print("note: --set is now --suite; --set will be removed in the next release", file=sys.stderr)
    try:
        return suites.load(a.suite)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(str(e))


def title(suite, any_version=False, run_mode="fix"):
    """Name used in report titles and file names: <suite name>, or 'all' without a suite (plus the mode if not fix)."""
    suffix = "" if run_mode == "fix" else f"-{run_mode}"
    if suite is None:
        return "all" + suffix
    return suite.name + ("-any-version" if any_version else "") + suffix


def provenance(suite, rows, any_version=False):
    """Markdown lines that tie a report to the suite version and instance hashes behind it."""
    if suite is None:
        return ["Scope: every recorded episode (no suite), so scenario versions may differ between rows."]
    lines = [f"Suite: **{suite.name} v{suite.version}** ({suite.visibility}, {len(suite.instances)} instances, "
             f"hint level {suite.hint_level}), fingerprint `{suites.fingerprint(suite)[:19]}`."]
    if any_version:
        lines.append("Matched by scenario id only (--any-version): rows may come from other scenario versions, "
                     "hint levels or prompt versions than the suite's, so these numbers are not pinned to it.")
    else:
        ran = {r.get("scenario") for r in rows}
        lines.append(f"Every row matches a member's content hash at hint level {suite.hint_level}, agent prompt "
                     f"version {PROMPT_VERSION}; "
                     f"{len(ran)} of {len(suite.instances)} members have results. "
                     "The suite file lists each member's hash; each result row records it as content_hash.")
    return lines


# ------------------------------------------------------------------ tags
_TAGS = None


def tags_of(r):
    """The row's tags: recorded with the episode, or (older rows) the scenario's current tags."""
    global _TAGS
    if r.get("tags"):
        return r["tags"]
    if _TAGS is None:
        import yaml
        _TAGS = {}
        for p in sorted((HERE.parent / "scenarios").glob("*/spec.yaml")):
            s = yaml.safe_load(p.read_text())
            _TAGS[s["id"]] = s["tags"]
    return _TAGS.get(r.get("scenario"), {"layer": r.get("layer") or r.get("family") or "unknown"})


def axis_values(r, axis):
    v = tags_of(r).get(axis)
    if v in (None, [], ""):
        return ["(none)"]
    return v if isinstance(v, list) else [v]


def axis_tables(rows, models, axes=AXES, counted=lambda r: r.get("status") == "done",
                passed=lambda r: bool(r.get("passed")), what="Pass rate"):
    """Markdown tables of passed/counted per tag value and model. An episode counts once under each value
    of a multi-valued axis (fix_type, drivers), so those columns can add up to more than the total."""
    out = []
    for axis in axes:
        cells = defaultdict(lambda: [0, 0])
        for r in rows:
            if not counted(r):
                continue
            for v in axis_values(r, axis):
                c = cells[(v, r["model"])]
                c[0] += passed(r)
                c[1] += 1
        groups = sorted({v for v, _ in cells})
        if not groups:
            continue
        multi = " (an episode counts under each of its values)" if axis != "layer" else ""
        out += ["", f"## {what} by {axis}{multi}", "", f"| {axis} | " + " | ".join(models) + " |",
                "|---|" + "---|" * len(models)]
        for g in groups:
            row = []
            for m in models:
                k, n = cells.get((g, m), (0, 0))
                row.append(f"{k}/{n} ({100 * k / n:.0f}%)" if n else "-")
            out.append(f"| {g} | " + " | ".join(row) + " |")
    return out
