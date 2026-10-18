"""Bring a broken world back, escalating step by step (shared by the validation harness and the benchmark, so a
world one run left broken never spills into the next run):

  1. wait a few minutes for it to settle
  2. re-apply the Helm chart (scripts/reset_world.sh)
  3. hard reset: restart every pod in the shop namespace. This also reloads the feature flags from their ConfigMap
     and makes every client reconnect from scratch (a gRPC client stuck on a dead connection, Kafka consumers).
"""
from __future__ import annotations

import subprocess
import time

from . import checks, kube
from .spec import REPO


def world_state(timeout):
    """(healthy?, the checks that are failing) after waiting up to `timeout` seconds for WORLD_HEALTHY."""
    from .harness import poll   # harness imports this module
    ok, res, _ = poll(checks.WORLD_HEALTHY, checks.PASS, timeout, quiet=True)
    return ok, [f"{n}: {d}"[:150] for n, s, d in res if s != checks.PASS]


def recover(log=print, settle_s=180):
    """(healthy?, notes on what was needed). Empty notes = the world was healthy within settle_s."""
    ok, bad = world_state(settle_s)
    if ok:
        return True, []
    notes = ["helm reset (" + "; ".join(bad) + ")"]
    log("World not healthy -> Helm reset. Failing: " + "; ".join(bad))
    r = subprocess.run(["bash", str(REPO / "scripts" / "reset_world.sh")], cwd=REPO,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        log("   reset_world.sh failed: " + (r.stdout + r.stderr)[-400:])
    ok, bad = world_state(240)
    if ok:
        return True, notes
    notes.append("hard reset (" + "; ".join(bad) + ")")
    log("Still unhealthy -> hard reset: restarting every pod in the shop namespace. Failing: " + "; ".join(bad))
    kube.kubectl("delete", "pod", "--all", "--wait=false", namespace=kube.APP_NS)
    time.sleep(30)
    ok, bad = world_state(900)
    if not ok:
        notes.append("still unhealthy after the hard reset (" + "; ".join(bad) + ")")
    return ok, notes
