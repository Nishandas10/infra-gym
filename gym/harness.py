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


def validate(spec_path, world_timeout=300):
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
        log(f"  3. verifier must FAIL (<= {v['detect_timeout_s']}s)")
        ok, _, t = poll(spec_checks, checks.FAIL, v["detect_timeout_s"], v["poll_s"])
        rec["timings"]["detect_s"] = t
        if not ok:
            rec["verdict"] = "NOT_DETECTED"
            return rec
        # The hold must outlast every stability window. Otherwise a pod that merely
        # got replaced (young) would count as a persistent failure.
        hold = max(v["hold_s"], min_age + 30)
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
