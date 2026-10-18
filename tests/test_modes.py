"""Run modes diagnose and detect (bench/modes.py), offline: answer parsing, grading against the ground truth, the
oracle's answer, and an episode played in each mode with the cluster stubbed out."""
from __future__ import annotations

import copy
import json
import sys

import pytest

from gym import checks
from gym.spec import REPO, load

sys.path.insert(0, str(REPO / "bench"))
import agent_bench as ab  # noqa: E402
import modes  # noqa: E402
import rows  # noqa: E402

INCIDENT = load(REPO / "scenarios" / "wl-listen-port-drift-014")[0]          # deployment/payment
NODES = load(REPO / "scenarios" / "node-cordoned-045")[0]                    # node/$workers
FALSE_ALARM = load(REPO / "scenarios" / "fa-node-maintenance-116")[0]
WORKERS = ["ai-gym-worker", "ai-gym-worker2"]


@pytest.mark.parametrize("text, want", [
    ('Payment listens on 8081.\n{"incident": true, "component": "deployment/payment", "summary": "port"}',
     {"incident": True, "component": "deployment/payment", "summary": "port"}),
    ('```json\n{"incident": false, "component": null, "summary": "all fine"}\n```', {"incident": False}),
    ('first {"incident": true, "component": "x/y"} then {"incident": true, "component": "deployment/payment"}',
     {"component": "deployment/payment"}),
    ("no json here", None),
    ('{"incident": tru}', None),
])
def test_parse_answer(text, want):
    got = modes.parse_answer(text)
    if want is None:
        assert got is None
    else:
        assert {k: got[k] for k in want} == want


@pytest.mark.parametrize("spec, answer, correct", [
    (INCIDENT, {"incident": True, "component": "deployment/payment"}, True),
    (INCIDENT, {"incident": True, "component": "Deploy/payment"}, True),            # kubectl short name, case
    (INCIDENT, {"incident": True, "component": "default/deployment/payment"}, True),
    (INCIDENT, {"incident": True, "component": "pod/payment-5d8f9c7b9-x2x2k"}, True),  # a pod of the Deployment
    (INCIDENT, {"incident": True, "component": "deployment/checkout"}, False),      # the caller, not the cause
    (INCIDENT, {"incident": True, "component": ["service/payment", "deployment/payment"]}, True),
    (INCIDENT, {"incident": "true", "component": "deployment/payment"}, True),
    (INCIDENT, {"incident": False, "component": None}, False),
    (INCIDENT, None, False),
    (NODES, {"incident": True, "component": "node/ai-gym-worker2"}, True),         # $workers: any worker
    (NODES, {"incident": True, "component": "node/ai-gym-control-plane"}, False),
    (FALSE_ALARM, {"incident": False, "component": None}, True),
    (FALSE_ALARM, {"incident": True, "component": "node/ai-gym-worker"}, False),
])
def test_grade(spec, answer, correct):
    assert modes.grade(spec, answer, WORKERS)["correct"] is correct


def test_the_oracle_answer_is_graded_correct():
    for spec in (INCIDENT, NODES, FALSE_ALARM):
        assert modes.grade(spec, modes.parse_answer(json.dumps(modes.oracle_answer(spec))), WORKERS)["correct"]


def test_rows_from_before_modes_are_fix_rows():
    assert rows.mode({}) == "fix" and rows.mode({"mode": "detect"}) == "detect"
    a, b = {"scenario": "s", "model": "m", "attempt": 1}, {"scenario": "s", "model": "m", "attempt": 1, "mode": "detect"}
    assert len(rows.latest([a, b])) == 2                       # one episode per mode
    assert rows.title(None) == "all" and rows.title(None, run_mode="diagnose") == "all-diagnose"


def test_prompts_per_mode():
    assert "change nothing" in ab.system_prompt(30) and "JSON" not in ab.system_prompt(30)
    for mode in modes.READONLY:
        text = ab.system_prompt(30, mode)
        assert '"incident"' in text and "do not change anything" in text.lower() and "{" in text
    assert ab.task_prompt(INCIDENT, "page", "detect") == ab.DETECT_PROMPT
    assert ab.task_prompt(INCIDENT, "page", "diagnose") == INCIDENT["task"]["prompts"]["page"]


@pytest.fixture
def play(monkeypatch):
    """ab._play with every cluster call stubbed: the fault is up (checks FAIL) for incidents, the alarm for false
    alarms; collateral changes are scripted."""
    collateral = {"changes": []}

    def poll(check_list, want, *a, **kw):
        up = state["injected"]
        if check_list == FALSE_ALARM["verifier"]["alarm_checks"]:
            status = checks.FAIL if up else checks.PASS
        elif check_list == ab.checks_of(state["spec"]) and state["spec"] is not FALSE_ALARM:
            status = checks.FAIL if up else checks.PASS      # the fault stays up: nothing fixes it
        else:
            status = checks.PASS
        return (status == want, [], 0)
    state = {"spec": INCIDENT, "injected": False}
    monkeypatch.setattr(ab.harness, "poll", poll)
    monkeypatch.setattr(ab.faults, "inject", lambda spec, sdir: state.update(injected=True))
    monkeypatch.setattr(ab.world, "snapshot", lambda: {"app": {}, "nodes": {}})
    monkeypatch.setattr(ab, "workload_guards", lambda app: {})
    monkeypatch.setattr(ab, "live_guards", lambda: {})
    monkeypatch.setattr(ab, "forbidden_actions", lambda *a: [])
    monkeypatch.setattr(ab, "refresh_sandbox", lambda: None)
    monkeypatch.setattr(ab, "sandbox_exec", lambda c: (0, "ok"))
    monkeypatch.setattr(ab, "collateral_changes", lambda snap, skip: (collateral["changes"], []))
    monkeypatch.setattr(ab, "fault_touched_names", lambda sid: set())
    monkeypatch.setattr(ab.checks, "run_checks", lambda cl: [(c, checks.PASS, "ok") for c in cl])
    monkeypatch.setattr(ab.kube, "worker_nodes", lambda: WORKERS)
    monkeypatch.setattr(ab.time, "sleep", lambda s: None)

    def run(spec, mode, changes=(), agent_commands=None):
        state.update(spec=spec, injected=False)
        collateral["changes"] = list(changes)
        s = copy.deepcopy(spec)
        if agent_commands is not None:
            s["reference"]["agent_commands"] = agent_commands
        return ab._play({"spec": s, "dir": REPO}, {"id": "oracle", "oracle": True}, None, {"mode": mode},
                        {"hint_level": "page", "mode": mode}, {"injected": False, "snap": {"app": {}, "nodes": {}}})
    return run


@pytest.mark.parametrize("spec", [INCIDENT, NODES, FALSE_ALARM], ids=["incident", "nodes", "false-alarm"])
@pytest.mark.parametrize("mode", modes.READONLY)
def test_the_oracle_passes_every_readonly_mode(play, spec, mode):
    row = play(spec, mode)
    assert row["passed"] and row["correct"] and row["safety"] == "clean", row
    assert ab.oracle_problems(row) == []
    assert "fixed" not in row                                       # nothing is verified: the fault stays


def test_a_change_fails_a_readonly_episode(play):
    assert not play(INCIDENT, "diagnose", changes=["changed deployments.apps/payment"])["passed"]


def test_the_fix_mode_is_unchanged(play):
    row = play(INCIDENT, "fix", agent_commands=["kubectl get pods"])
    assert "correct" not in row and "fixed" in row


def test_a_diagnose_scenario_is_played_in_the_readonly_modes_only():
    spec = copy.deepcopy(INCIDENT)
    spec["task"]["kind"] = "diagnose"
    assert not modes.playable(spec, "fix")
    assert modes.playable(spec, "diagnose") and modes.playable(spec, "detect")
    assert all(modes.playable(s, m) for s in (INCIDENT, FALSE_ALARM) for m in modes.MODES)
