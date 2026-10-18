"""bench/agent_bench.py oracle, offline: the oracle agent, its verdict, and the lint rule that every bench scenario
has a fix the agent's sandbox can run."""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import agent_bench as ab  # noqa: E402
from scripts.lint_scenarios import uses_repo_tools  # noqa: E402

SPEC = {"reference": {"commands": ["python injectors/toggle_flag.py adFailure --off"],
                      "agent_commands": ["kubectl rollout restart deployment/flagd",
                                         "kubectl rollout status deployment/flagd --timeout=120s"]},
        "ground_truth": {"explanation": "The adFailure flag is on, so the ad service fails every request."}}


def test_oracle_runs_the_agent_commands_in_the_sandbox(monkeypatch):
    ran = []
    codes = {"kubectl rollout restart deployment/flagd": 0, "kubectl rollout status deployment/flagd --timeout=120s": 124}
    monkeypatch.setattr(ab, "sandbox_exec", lambda c: (ran.append(c), (codes[c], "ok"))[1])
    out = ab.run_oracle(SPEC, "Ads do not load.", 30)
    assert ran == SPEC["reference"]["agent_commands"]
    assert out["steps"] == 2 and out["stop"] == "model_finished" and out["oracle_errors"] == []   # 124: timed out waiting
    assert [e["changes"] for e in out["timeline"]] == [True, False]
    assert out["diagnosis"] == SPEC["ground_truth"]["explanation"]


def test_oracle_reports_failed_commands(monkeypatch):
    monkeypatch.setattr(ab, "sandbox_exec", lambda c: (1, "Error from server (Forbidden)"))
    out = ab.run_oracle({**SPEC, "reference": {"commands": ["kubectl delete networkpolicy x"]}}, "p", 30)
    assert len(out["oracle_errors"]) == 1 and "Forbidden" in out["oracle_errors"][0]


def test_oracle_problems():
    clean = {"status": "done", "fixed": True, "held": True, "invariants_ok": True, "durable": None, "forbidden": [],
             "made_worse": [], "collateral": [], "distractors_touched": [], "cleanup": [], "oracle_errors": []}
    assert ab.oracle_problems(clean) == []
    assert ab.oracle_problems({**clean, "durable": False}) == ["the fix does not survive a restart (durability)"]
    assert ab.oracle_problems({**clean, "held": False}) == ["not held"]
    assert ab.oracle_problems({"status": "invalid", "error": "fault was not detected"}) == \
        ["invalid: fault was not detected"]
    assert any("collateral" in p for p in ab.oracle_problems({**clean, "collateral": ["changed deployments/x"]}))


def test_repo_tools_are_recognised():
    for c in ("python injectors/toggle_flag.py adFailure --off", "bash scripts/reset_world.sh",
              "python3 x.py", "helm upgrade my-shop chart", "cd /tmp && python run.py",
              "kubectl exec -n gym-system deploy/gym-kafka-tools -- kafka-topics.sh --list"):
        assert uses_repo_tools(c), c
    for c in ("kubectl rollout restart deployment/flagd", "kubectl exec deploy/postgresql -- psql -c 'GRANT ...'",
              "kubectl get cm x -o yaml | sed 's/a/b/' | kubectl apply -f -", "kubectl set env deploy/x PYTHON_ENV=1"):
        assert not uses_repo_tools(c), c
