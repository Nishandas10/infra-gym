"""gym/recovery.py, offline: the order pipeline check before episodes, and the escalation when the world is broken."""
from __future__ import annotations

import pytest

from gym import checks, harness, kube, recovery


@pytest.fixture
def world(monkeypatch):
    """A scripted world: `state` says which check lists pass; records restarts, Helm resets and pod deletions."""
    state = {"world": True, "pipeline": True, "fix_pipeline_on_restart": True, "restarted": [], "helm": 0,
             "deleted": 0, "polled": []}

    def poll(check_list, want, timeout, interval=10, quiet=False):
        state["polled"].append((check_list[0]["type"], timeout))
        ok = state["pipeline"] if check_list is recovery.PIPELINE else state["world"]
        status = checks.PASS if ok else checks.FAIL
        return ok, [(checks.describe(c), status, "scripted") for c in check_list], 7

    def rollout_restart(kind, name, namespace=kube.APP_NS):
        state["restarted"].append(f"{kind}/{name}")
        if state["fix_pipeline_on_restart"]:
            state["pipeline"] = True

    def helm(*args, **kwargs):
        state["helm"] += 1
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    def kubectl(*args, **kwargs):
        if args[:2] == ("delete", "pod"):
            state["deleted"] += 1
            state["world"] = state["pipeline"] = True
        return ""

    monkeypatch.setattr(harness, "poll", poll)
    monkeypatch.setattr(kube, "rollout_restart", rollout_restart)
    monkeypatch.setattr(kube, "kubectl", kubectl)
    monkeypatch.setattr(recovery.subprocess, "run", helm)
    monkeypatch.setattr(recovery.time, "sleep", lambda s: None)
    return state


def test_a_healthy_world_checks_the_order_pipeline_too(world):
    assert recovery.recover(log=lambda m: None) == (True, [])
    assert [t for t, _ in world["polled"]] == ["pods_ready", "orders_recorded"]
    assert world["polled"][1][1] == 180 - 7          # what was left of the settle time


def test_the_pipeline_is_not_checked_while_the_world_is_broken(world):
    world["world"] = False
    ok, bad = recovery.world_state(60)
    assert not ok and all(not b.startswith("orders_recorded") for b in bad)
    assert [t for t, _ in world["polled"]] == ["pods_ready"]


def test_a_wedged_pipeline_gets_a_client_restart_not_a_reset(world):
    world["pipeline"] = False
    ok, notes = recovery.recover(log=lambda m: None)
    assert ok and world["restarted"] == ["deployment/checkout", "deployment/accounting"]
    assert world["helm"] == 0 and world["deleted"] == 0
    assert len(notes) == 1 and notes[0].startswith("restart checkout + accounting (orders_recorded")


def test_a_pipeline_the_restart_does_not_fix_escalates(world):
    world.update(pipeline=False, fix_pipeline_on_restart=False)
    ok, notes = recovery.recover(log=lambda m: None)
    assert ok and world["helm"] == 1 and world["deleted"] == 1      # Helm reset, then the hard reset fixed it
    assert [n.split(" (")[0] for n in notes] == ["restart checkout + accounting", "helm reset", "hard reset"]


def test_other_failures_skip_the_client_restart(world):
    world["world"] = False
    recovery.recover(log=lambda m: None)
    assert world["restarted"] == [] and world["helm"] == 1


def test_grading_checks_are_unchanged():
    """The pipeline check is for before episodes only: WORLD_HEALTHY (damage) and shop_health (invariants) do not
    include it, so how episodes are graded does not change."""
    assert all(c["type"] != "orders_recorded" for c in checks.WORLD_HEALTHY + checks.INVARIANTS["shop_health"])
