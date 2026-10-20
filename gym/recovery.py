"""Bring a broken world back, escalating step by step (shared by the validation harness and the benchmark, so a
world one run left broken never spills into the next run):

  1. wait a few minutes for it to settle
  2. if only orders are not being recorded: restart checkout and accounting (a wedged Kafka client)
  3. re-apply the Helm chart (scripts/reset_world.sh)
  4. hard reset: restart every pod in the shop namespace. This also reloads the feature flags from their ConfigMap
     and makes every client reconnect from scratch (a gRPC client stuck on a dead connection, Kafka consumers).
"""
from __future__ import annotations

import subprocess
import time

from . import checks, kube
from .spec import REPO

# The order pipeline end to end (checkout -> Kafka -> accounting -> Postgres), checked with WORLD_HEALTHY before every
# episode and in preflight. It is NOT part of WORLD_HEALTHY, which also judges damage after the agent: grading stays
# as it is. It catches a wedged Kafka producer in checkout (ai-gym-2, 2026-10-20): the shop passed every
# WORLD_HEALTHY check for hours while orders reached Kafka only about once a minute, so scenarios that check
# orders_recorded failed at random.
PIPELINE = [{"type": "orders_recorded", "timeout_s": 60}]
PIPELINE_CLIENTS = ("checkout", "accounting")   # restarted when only the pipeline fails


def world_state(timeout):
    """(healthy?, the checks that are failing) after waiting up to `timeout` seconds for WORLD_HEALTHY, then the
    order pipeline (tried at least once, within what is left of the timeout)."""
    from .harness import poll   # harness imports this module
    ok, res, waited = poll(checks.WORLD_HEALTHY, checks.PASS, timeout, quiet=True)
    if ok:
        ok, res, _ = poll(PIPELINE, checks.PASS, max(0, timeout - waited), quiet=True)
    return ok, [f"{n}: {d}"[:150] for n, s, d in res if s != checks.PASS]


def only_pipeline(bad):
    """True if the order pipeline is the only thing failing."""
    return bool(bad) and all(b.startswith(PIPELINE[0]["type"]) for b in bad)


def recover(log=print, settle_s=180):
    """(healthy?, notes on what was needed). Empty notes = the world was healthy within settle_s."""
    ok, bad = world_state(settle_s)
    if ok:
        return True, []
    notes = []
    if only_pipeline(bad):
        notes.append(f"restart {' + '.join(PIPELINE_CLIENTS)} (" + "; ".join(bad) + ")")
        log("Orders are not recorded although the shop looks healthy -> restarting "
            f"{' and '.join(PIPELINE_CLIENTS)} (a wedged Kafka client)")
        for name in PIPELINE_CLIENTS:
            kube.rollout_restart("deployment", name)
        ok, bad = world_state(300)
        if ok:
            return True, notes
    notes.append("helm reset (" + "; ".join(bad) + ")")
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
