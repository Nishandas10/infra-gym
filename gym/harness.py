"""Validation harness: proves a scenario really works, end to end.

For each scenario:
  0. world healthy       the whole shop passes WORLD_HEALTHY checks
  1. baseline PASS       the scenario's own checks pass before injecting
  2. inject              break the system as the spec says
  3. detect FAIL         the verifier notices (within detect_timeout_s)
  4. hold                a do-nothing agent is still failing hold_s later
  5. reference solution  run the documented fix (spec.reference.commands)
  6. recover PASS        the verifier passes again (within recover_timeout_s)
     6b. invariants       ... and so do the invariants (shop_health: every user journey)
     6c. durability       ... and the checks still pass after restarting verifier.durability
  7. restore             undo the injection exactly, then WORLD_HEALTHY again

A false alarm (task.kind false_alarm) has nothing to fix; after step 2 it runs instead:
  3. alarm raised        verifier.alarm_checks FAIL (within detect_timeout_s): the alarm is really there
  3b. healthy            the scenario's checks PASS (within recover_timeout_s; a stale alarm may need to clear)
  4. hold                ... and keep passing for hold_s: the alarm breaks nothing
  6b. invariants         every user journey passes
then 7. restore, as above.

Timings come from the instance (spec.validation, resolved from templates/defaults.yaml).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

from . import checks, faults, kube
from .spec import REPO, checks_of, fault_label, load

RESULTS = REPO / "results" / "validation.jsonl"
ENVIRONMENTS = REPO / "results" / "environments.jsonl"
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


STALE_ROLLOUT_RETRIES = 6   # 10 s apart; see run_solution


def run_solution(commands):
    # Reference fixes call repo scripts as `python ...`: make that the interpreter running the
    # harness (e.g. the venv's), even when the venv is not activated.
    env = dict(os.environ, PATH=os.pathsep.join([os.path.dirname(sys.executable), os.environ.get("PATH", "")]))
    for cmd in commands:
        log(f"    $ {cmd}")
        for attempt in range(STALE_ROLLOUT_RETRIES + 1):
            r = subprocess.run(["bash", "-c", cmd], cwd=REPO, capture_output=True, text=True, timeout=900, env=env)
            out = (r.stdout + r.stderr).strip()
            if out:
                for line in out.splitlines()[-4:]:
                    log(f"      {line[:160]}")
            # A fault left in place longer than the Deployment's progress deadline (600 s) marks its rollout
            # ProgressDeadlineExceeded. Right after the fix, `rollout status` can still read that condition
            # before the controller has started the new rollout, and fails at once: wait and ask again.
            if r.returncode != 0 and "rollout status" in cmd and "exceeded its progress deadline" in out \
                    and attempt < STALE_ROLLOUT_RETRIES:
                log("      (stale progress-deadline condition from the fault's rollout; retrying)")
                time.sleep(10)
                continue
            break
        if r.returncode != 0:
            raise RuntimeError(f"solution command failed (exit {r.returncode}): {cmd}")


def _run(cmd, timeout=60):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {(r.stderr or r.stdout).strip()[:200]}")
    return r.stdout


def git_state(exclude=("results",)):
    """The repo commit the run used, and whether code differed from it (the `exclude` paths not counted)."""
    try:
        sha = _run(["git", "rev-parse", "HEAD"]).strip()
        dirty = bool(_run(["git", "status", "--porcelain", "--", ".", *(f":(exclude){p}" for p in exclude)]).strip())
        return sha, dirty
    except Exception:
        return None, None


def environment():
    """What the world ran: Helm chart, every workload image, Kubernetes, kubelet and kind versions.

    Saved once per distinct value in results/environments.jsonl; a validation record points at it
    by `env` (a hash of the content)."""
    env = {}
    try:
        env["charts"] = sorted(f"{r['name']}={r['chart']} (app {r['app_version']})"
                               for r in json.loads(_run(["helm", "list", "-n", kube.APP_NS, "-o", "json"])))
    except Exception as e:
        env["charts"] = f"unknown: {type(e).__name__}"
    images = {}
    for kind in ("deployments", "daemonsets", "statefulsets"):
        for obj in kube.items(kind, namespace=kube.APP_NS):
            spec = obj["spec"]["template"]["spec"]
            images[f"{kind[:-1]}/{obj['metadata']['name']}"] = sorted(
                c["image"] for c in spec.get("containers", []) + spec.get("initContainers", []))
    env["images"] = images
    env["kubernetes"] = json.loads(kube.kubectl("version", "-o", "json", namespace=None))["serverVersion"]["gitVersion"]
    env["nodes"] = sorted({f"{n['status']['nodeInfo']['kubeletVersion']} {n['status']['nodeInfo']['containerRuntimeVersion']}"
                           for n in kube.items("nodes", namespace=None)})
    try:
        env["kind"] = _run(["kind", "version"]).strip()
    except Exception:
        env["kind"] = None
    env_id = "env:" + hashlib.sha256(json.dumps(env, sort_keys=True).encode()).hexdigest()[:16]
    known = ENVIRONMENTS.read_text() if ENVIRONMENTS.exists() else ""
    if f'"id": "{env_id}"' not in known:
        ENVIRONMENTS.parent.mkdir(exist_ok=True)
        with ENVIRONMENTS.open("a") as fh:
            fh.write(json.dumps({"id": env_id, "first_seen": datetime.datetime.now().isoformat(timespec="seconds"),
                                 **env}) + "\n")
    return env_id


def kube_context():
    """The cluster the run talks to (kubectl's current context, from KUBECONFIG)."""
    try:
        return kube.kubectl("config", "current-context", namespace=None).strip()
    except Exception:
        return None


def stable_age(spec_checks):
    """A stability check needs at least its own window to pass after recent restarts."""
    return max([c.get("min_age_s", 0) for c in spec_checks if c["type"] == "pods_stable"] or [0])


def restart_durability_targets(spec):
    """Restart the workloads in verifier.durability (as a node drain or a deploy would)."""
    from .undo import restart
    for r in spec["verifier"]["durability"]:
        restart(r["restart"], r.get("namespace") or kube.APP_NS)


def durability_check(spec, spec_checks, v):
    """Restart verifier.durability targets, let them come back, then require PASS again: a fix
    that only patched live state is lost on the next restart."""
    log(f"  6c. the fix must survive a restart of {', '.join(r['restart'] for r in spec['verifier']['durability'])}")
    restart_durability_targets(spec)
    time.sleep(v["restart_settle_s"])
    ok, _, t = poll(spec_checks, checks.PASS, v["recover_timeout_s"] + stable_age(spec_checks), v["poll_s"])
    return ok, t


def is_false_alarm(spec):
    return spec["task"].get("kind") == "false_alarm"


def validate_false_alarm(spec, rec, spec_checks, invariants, hold_s):
    """Steps 3-6 of a false alarm (see the module docstring). Sets and returns rec; validate() restores."""
    v = spec["validation"]
    log(f"  3. the alarm must be raised: alarm checks FAIL (<= {v['detect_timeout_s']}s)")
    ok, _, t = poll(spec["verifier"]["alarm_checks"], checks.FAIL, v["detect_timeout_s"], v["poll_s"])
    rec["timings"]["alarm_s"] = t
    if not ok:
        rec["verdict"] = "ALARM_NOT_RAISED"
        return rec
    log(f"  3b. nothing is broken: the checks must PASS (<= {v['recover_timeout_s']}s)")
    ok, _, t = poll(spec_checks, checks.PASS, v["recover_timeout_s"], v["poll_s"])
    rec["timings"]["healthy_s"] = t
    if not ok:
        rec["verdict"] = "NOT_HEALTHY_UNDER_ALARM"
        return rec
    hold = max(hold_s or v["hold_s"], stable_age(spec_checks) + 30)
    rec["hold_s"] = hold
    log(f"  4. the checks must keep passing for {hold}s")
    t_end = time.time() + hold
    fails = polls = 0
    while time.time() < t_end:
        time.sleep(min(v["poll_s"], max(0, t_end - time.time())))
        polls += 1
        res = checks.run_checks(spec_checks)
        if checks.overall(res) == checks.FAIL:
            fails += 1
            res = checks.run_checks(spec_checks)   # confirm, so one flaky request is not a broken service
            if checks.overall(res) == checks.FAIL:
                show(res)
                rec["hold_fail_ratio"] = f"{fails}/{polls}"
                rec["verdict"] = "ALARM_IS_REAL"
                return rec
    rec["hold_fail_ratio"] = f"{fails}/{polls}"
    log(f"      unconfirmed failures in {fails}/{polls} checks during the hold")
    if invariants:
        log(f"  6b. invariants must PASS ({', '.join(spec['verifier']['invariants'])})")
        ok, _, t = poll(invariants, checks.PASS, v["recover_timeout_s"], v["poll_s"])
        rec["timings"]["invariants_s"] = t
        if not ok:
            rec["verdict"] = "INVARIANT_FAILED"
            return rec
    rec["verdict"] = "VALIDATED"
    return rec


def validate(spec_path, world_timeout=300, hold_s=None):
    """One validation run. hold_s overrides the do-nothing hold of step 4; a long hold (the agent's whole
    wall-clock budget) proves the fault stays broken for as long as an episode can last."""
    global _logfile
    spec, sdir = load(spec_path)
    sid = spec["id"]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _logfile = LOG_DIR / f"{sid}.log"
    _logfile.write_text("")
    v = spec["validation"]
    spec_checks = checks_of(spec)
    invariants = checks.invariant_checks(spec)
    min_age = stable_age(spec_checks)
    rec = {"id": sid, "type": fault_label(spec), "validation_hash": spec["validation_hash"],
           "content_hash": spec["content_hash"], "template_version": spec["instance_of"]["version"],
           "git_sha": None, "git_dirty": None, "env": None, "context": kube_context(),
           "started": datetime.datetime.now().isoformat(timespec="seconds"),
           "hold_mode": "long" if hold_s else "normal",
           "timings": {}, "verdict": None, "notes": []}
    log(f"=== {sid} ({fault_label(spec)})")
    injected = False
    try:
        rec["git_sha"], rec["git_dirty"] = git_state()
        try:
            rec["env"] = environment()
        except Exception as e:   # a missing fingerprint must not stop the run; the record says why
            rec["notes"].append(f"environment unknown: {type(e).__name__}: {e}"[:200])
        log("  0. world healthy?")
        ok, _, t = poll(checks.WORLD_HEALTHY, checks.PASS, world_timeout, quiet=True)
        rec["timings"]["world_ready_s"] = t
        if not ok:
            poll(checks.WORLD_HEALTHY, checks.PASS, 0)
            rec["verdict"] = "ENV_UNHEALTHY"
            return rec
        log("  1. baseline must PASS")
        ok, _, t = poll(spec_checks, checks.PASS, max(v["baseline_timeout_s"], min_age + 90))
        if not ok:
            rec["verdict"] = "BASELINE_FAIL"
            return rec
        log("  2. inject")
        injected = True
        faults.inject(spec, sdir)
        if is_false_alarm(spec):
            return validate_false_alarm(spec, rec, spec_checks, invariants, hold_s)
        log(f"  3. verifier must FAIL (<= {v['detect_timeout_s']}s)")
        ok, _, t = poll(spec_checks, checks.FAIL, v["detect_timeout_s"], v["poll_s"])
        rec["timings"]["detect_s"] = t
        if not ok:
            rec["verdict"] = "NOT_DETECTED"
            return rec
        # The hold must outlast every stability window. Otherwise a pod that merely
        # got replaced (young) would count as a persistent failure.
        hold = max(hold_s or v["hold_s"], min_age + 30)
        rec["hold_s"] = hold
        log(f"  4. do-nothing agent: still FAIL after {hold}s?")
        # Keep exercising the system during the hold, as real users would; some faults
        # (leaks) only get worse with traffic.
        t_end = time.time() + hold
        fails = polls = 0
        while time.time() < t_end - v["poll_s"]:
            time.sleep(v["poll_s"])
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
        log(f"  6. verifier must PASS (<= {v['recover_timeout_s']}s)")
        ok, _, t = poll(spec_checks, checks.PASS, v["recover_timeout_s"], v["poll_s"])
        rec["timings"]["recover_s"] = t
        if not ok:
            rec["verdict"] = "FIX_DID_NOT_RECOVER"
            return rec
        if invariants:
            # The fix must not leave (or cause) breakage elsewhere in the shop.
            log(f"  6b. invariants must PASS ({', '.join(spec['verifier']['invariants'])})")
            ok, _, t = poll(invariants, checks.PASS, v["recover_timeout_s"], v["poll_s"])
            rec["timings"]["invariants_s"] = t
            if not ok:
                rec["verdict"] = "INVARIANT_FAILED"
                return rec
        if spec["verifier"]["durability"]:
            ok, t = durability_check(spec, spec_checks, v)
            rec["timings"]["durable_s"] = t
            if not ok:
                rec["verdict"] = "FIX_NOT_DURABLE"
                return rec
        rec["verdict"] = "VALIDATED"
        return rec
    except KeyboardInterrupt:   # stopped by hand: revert below, and the record does not count as evidence
        rec["verdict"] = "INTERRUPTED"
        raise
    except Exception as e:
        rec["verdict"] = "ERROR"
        rec["notes"].append(f"{type(e).__name__}: {e}")
        log("  ERROR " + "".join(traceback.format_exception_only(e)).strip())
        return rec
    finally:
        now_ctx = kube_context()
        if now_ctx != rec["context"]:   # e.g. `kind create cluster` switched the default context
            # Reverting now would undo the fault on the wrong cluster: keep the undo log for a human.
            rec["verdict"] = "ENV_CHANGED"
            rec["notes"].append(f"cluster context changed during the run ({rec['context']} -> {now_ctx}); not reverted: "
                                f"run injectors/inject.py --revert against {rec['context']}")
            log(f"  ! {rec['notes'][-1]}")
        if injected and rec["verdict"] != "ENV_CHANGED":
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
        if rec["verdict"] != "VALIDATED":   # keep failure logs; the next run of this scenario overwrites {sid}.log
            (LOG_DIR / "failed").mkdir(exist_ok=True)
            shutil.copy(_logfile, LOG_DIR / "failed" / f"{sid}-{rec['started'].replace(':', '')}.log")
