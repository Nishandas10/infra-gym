"""One job per cluster. Every command that changes a cluster (validation, benchmark runs, the oracle, preflight,
inject/revert) holds that cluster's lock while it runs, so a second job on the same cluster refuses to start instead
of injecting a fault into a world another episode is using.

The lock is machine-wide (not per checkout) and keyed by the kube context, so two checkouts or two KUBECONFIG files
that point at the same cluster share it. It is an flock: it goes away when the process ends, even on a crash.
"""
from __future__ import annotations

import fcntl
import os
import pathlib
import re
import subprocess
import sys

LOCK_DIR = pathlib.Path(os.environ.get("GYM_LOCK_DIR") or pathlib.Path.home() / ".cache" / "infra-gym" / "locks")
_held = []   # open lock files: kept for the life of the process


def current_context():
    try:
        out = subprocess.run(["kubectl", "config", "current-context"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or "default"
    except (OSError, subprocess.TimeoutExpired):
        return "default"


def hold_cluster(what, context=None):
    """Take this cluster's lock for the rest of the process, or exit naming the job that holds it."""
    ctx = context or current_context()
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    f = open(LOCK_DIR / (re.sub(r"[^\w.-]", "_", ctx) + ".lock"), "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.seek(0)
        holder = f.read().strip() or "another job"
        f.close()
        sys.exit(f"cluster {ctx} is in use ({holder}): one job per cluster. Wait for it, or use another cluster.")
    f.seek(0)
    f.truncate()
    f.write(f"{what}, pid {os.getpid()}\n")
    f.flush()
    _held.append(f)
    return ctx
