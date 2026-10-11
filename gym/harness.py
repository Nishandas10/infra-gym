"""Validation harness: proves a scenario really works, end to end.

For each scenario:
  0. world healthy       the whole shop passes WORLD_HEALTHY checks
  1. baseline PASS       the scenario's own checks pass before injecting
  2. inject              break the system as the spec says
  3. detect FAIL         the verifier notices (within detect_timeout_s)
  4. hold                a do-nothing agent is still failing hold_s later
  5. reference solution  run the documented fix (spec.reference.commands)
  6. recover PASS        the verifier passes again (within recover_timeout_s)
  7. restore             undo the injection exactly, then WORLD_HEALTHY again
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import time
import traceback

from . import checks, faults
from .spec import REPO, checks_of, fault_label, load

RESULTS = REPO / "results" / "validation.jsonl"
LOG_DIR = REPO / "results" / "logs"
_logfile = None


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    if _logfile:
        with open(_logfile, "a") as fh:
            fh.write(line + "\n")


def show(results):
    for c, status, msg in results:
        log(f"      [{status:7s}] {checks.describe(c)} - {msg}")


def poll(check_list, want, timeout, interval=10, quiet=False):
    t0 = time.time()
    while True:
        res = checks.run_checks(check_list)
        status = checks.overall(res)
        if status == want or time.time() - t0 >= timeout:
            if not quiet:
                show(res)
            return status == want, res, round(time.time() - t0)
        time.sleep(interval)


def run_solution(commands):
    # Reference fixes call repo scripts as `python ...`: make that the interpreter running the
    # harness (e.g. the venv's), even when the venv is not activated.
    env = dict(os.environ, PATH=os.pathsep.join([os.path.dirname(sys.executable), os.environ.get("PATH", "")]))
    for cmd in commands:
        log(f"    $ {cmd}")
        r = subprocess.run(["bash", "-c", cmd], cwd=REPO, capture_output=True, text=True, timeout=900, env=env)
        out = (r.stdout + r.stderr).strip()
        if out:
            for line in out.splitlines()[-4:]:
                log(f"      {line[:160]}")
        if r.returncode != 0:
            raise RuntimeError(f"solution command failed (exit {r.returncode}): {cmd}")


def durability_check(spec_checks, v):
    """Restart validation.restart_after_fix targets, let them come back, then require PASS."""
    from .undo import restart
    log(f"  6b. the fix must survive a restart of {', '.join(v['restart_after_fix'])}")
    for target in v["restart_after_fix"]:
        restart(target)
    time.sleep(v.get("restart_settle_s", 45))
    ok, _, t = poll(spec_checks, checks.PASS, v.get("recover_timeout_s", 300), v.get("poll_s", 10))
    return ok, t


def validate(spec_path, world_timeout=300):
    global _logfile
    spec, sdir = load(spec_path)
    sid = spec["id"]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _logfile = LOG_DIR / f"{sid}.log"
    _logfile.write_text("")
    v = spec.get("validation") or {}
    spec_checks = checks_of(spec)
    rec = {"id": sid, "type": fault_label(spec), "validation_hash": spec["validation_hash"],
           "content_hash": spec["content_hash"], "template_version": spec["instance_of"]["version"],
           "started": datetime.datetime.now().isoformat(timespec="seconds"),
           "timings": {}, "verdict": None, "notes": []}
    log(f"=== {sid} ({fault_label(spec)})")
    injected = False
    try:
        log("  0. world healthy?")
        ok, _, t = poll(checks.WORLD_HEALTHY, checks.PASS, world_timeout, quiet=True)
        rec["timings"]["world_ready_s"] = t
        if not ok:
            poll(checks.WORLD_HEALTHY, checks.PASS, 0)
            rec["verdict"] = "ENV_UNHEALTHY"
            return rec
        log("  1. baseline must PASS")
        # A stability check needs at least its own window to pass after recent restarts.
        stable_age = max([c.get("min_age_s", 0) for c in spec_checks if c["type"] == "pods_stable"] or [0])
        ok, _, t = poll(spec_checks, checks.PASS, max(v.get("baseline_timeout_s", 120), stable_age + 90))
        if not ok:
            rec["verdict"] = "BASELINE_FAIL"
            return rec
        log("  2. inject")
        injected = True
        faults.inject(spec, sdir)
        log(f"  3. verifier must FAIL (<= {v.get('detect_timeout_s', 240)}s)")
        ok, _, t = poll(spec_checks, checks.FAIL, v.get("detect_timeout_s", 240), v.get("poll_s", 10))
        rec["timings"]["detect_s"] = t
        if not ok:
            rec["verdict"] = "NOT_DETECTED"
            return rec
        # The hold must outlast every stability window. Otherwise a pod that merely
        # got replaced (young) would count as a persistent failure.
        hold = max(v.get("hold_s", 30), stable_age + 30)
        log(f"  4. do-nothing agent: still FAIL after {hold}s?")
        # Keep exercising the system during the hold, as real users would; some faults
        # (leaks) only get worse with traffic.
        t_end = time.time() + hold
        fails = polls = 0
        while time.time() < t_end - v.get("poll_s", 10):
            time.sleep(v.get("poll_s", 10))
            polls += 1
            fails += checks.overall(checks.run_checks(spec_checks)) == checks.FAIL
        time.sleep(max(0, t_end - time.time()))
        res = checks.run_checks(spec_checks)
        show(res)
        rec["hold_fail_ratio"] = f"{fails}/{polls}"
        log(f"      failing in {fails}/{polls} checks during the hold")
        if checks.overall(res) == checks.PASS:
            rec["verdict"] = "SELF_HEALED"
            return rec
        log("  5. reference solution")
        run_solution(spec["reference"]["commands"])
        log(f"  6. verifier must PASS (<= {v.get('recover_timeout_s', 300)}s)")
        ok, _, t = poll(spec_checks, checks.PASS, v.get("recover_timeout_s", 300), v.get("poll_s", 10))
        rec["timings"]["recover_s"] = t
        if ok and v.get("restart_after_fix"):
            # Some scenarios only count a fix that is in the source of truth: restart the
            # listed workloads (as a node drain or a deploy would) and require PASS again.
            ok, t = durability_check(spec_checks, v)
            rec["timings"]["durable_s"] = t
            if not ok:
                rec["verdict"] = "FIX_NOT_DURABLE"
                return rec
        rec["verdict"] = "VALIDATED" if ok else "FIX_DID_NOT_RECOVER"
        return rec
    except Exception as e:
        rec["verdict"] = "ERROR"
        rec["notes"].append(f"{type(e).__name__}: {e}")
        log("  ERROR " + "".join(traceback.format_exception_only(e)).strip())
        return rec
    finally:
        if injected:
            log("  7. restore exactly")
            errors = faults.revert(spec)
            if errors:
                rec["notes"] += [f"revert: {e}" for e in errors]
                log(f"      revert errors: {errors}")
            ok, _, t = poll(checks.WORLD_HEALTHY, checks.PASS, world_timeout, quiet=True)
            rec["timings"]["restore_s"] = t
            if not ok:
                poll(checks.WORLD_HEALTHY, checks.PASS, 0)
                rec["notes"].append("world not healthy after restore")
                if rec["verdict"] == "VALIDATED":
                    rec["verdict"] = "RESTORE_FAILED"
        rec["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
        RESULTS.parent.mkdir(exist_ok=True)
        with RESULTS.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        log(f"  => {rec['verdict']}  {rec['timings']}")
