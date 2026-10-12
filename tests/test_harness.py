"""The validation harness's verdicts (gym/harness.py), with scripted check results and a fake clock.

The cluster is not touched: injection, the reference fix and restarts only move a scripted
world between phases, and each check list reports what that phase should look like.
"""
from __future__ import annotations

import time as real_time

import pytest

from gym import checks, harness, undo
from gym.spec import REPO

SPEC = REPO / "scenarios" / "wl-listen-port-drift-014"   # durability: deployment/payment; invariants: shop_health


class Clock:
    """Stands in for the harness's `time` module: sleeping advances the clock instantly."""
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += max(s, 0.01)

    def strftime(self, fmt):
        return real_time.strftime(fmt)


class World:
    """healthy -> faulted (inject) -> fixed (reference fix) -> restarted (durability)."""
    def __init__(self, invariants_after_fix=checks.PASS, checks_after_restart=checks.PASS):
        self.phase = "healthy"
        self.invariants_after_fix = invariants_after_fix
        self.checks_after_restart = checks_after_restart
        self.restarted = []

    def run_checks(self, check_list):
        if check_list is checks.WORLD_HEALTHY:
            status = checks.PASS if self.phase in ("healthy", "restored") else checks.FAIL
        elif check_list == checks.INVARIANTS["shop_health"]:
            status = self.invariants_after_fix
        elif self.phase in ("healthy", "fixed", "restored"):
            status = checks.PASS
        elif self.phase == "restarted":
            status = self.checks_after_restart
        else:
            status = checks.FAIL
        return [(c, status, "scripted") for c in check_list]


@pytest.fixture
def world(monkeypatch, tmp_path):
    def make(**kw):
        w = World(**kw)
        monkeypatch.setattr(harness, "time", Clock())
        monkeypatch.setattr(harness, "RESULTS", tmp_path / "validation.jsonl")
        monkeypatch.setattr(harness, "LOG_DIR", tmp_path / "logs")
        monkeypatch.setattr(checks, "run_checks", w.run_checks)
        monkeypatch.setattr(harness.faults, "inject", lambda spec, sdir: setattr(w, "phase", "faulted"))
        monkeypatch.setattr(harness.faults, "revert", lambda spec: setattr(w, "phase", "restored") or [])
        monkeypatch.setattr(harness, "run_solution", lambda commands: setattr(w, "phase", "fixed"))

        def restart(target, namespace):
            w.restarted.append((target, namespace))
            w.phase = "restarted"
        monkeypatch.setattr(undo, "restart", restart)
        return w
    return make


def test_validated(world):
    w = world()
    rec = harness.validate(SPEC)
    assert rec["verdict"] == "VALIDATED", rec
    assert w.restarted == [("deployment/payment", "default")]
    assert {"recover_s", "invariants_s", "durable_s"} <= set(rec["timings"])


def test_a_fix_that_breaks_another_journey_fails_the_invariant(world):
    w = world(invariants_after_fix=checks.FAIL)
    rec = harness.validate(SPEC)
    assert rec["verdict"] == "INVARIANT_FAILED"
    assert w.restarted == []          # durability is not tried after a failed invariant


def test_a_fix_lost_on_restart_is_not_durable(world):
    world(checks_after_restart=checks.FAIL)
    assert harness.validate(SPEC)["verdict"] == "FIX_NOT_DURABLE"


def test_default_hold_is_60s(world):
    world()
    rec = harness.validate(SPEC)
    # 60 s hold, polled every 10 s: the last poll is skipped so the final check lands at 60 s
    assert rec["hold_fail_ratio"] == "5/5"
