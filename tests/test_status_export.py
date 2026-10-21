"""agent_bench.py status and bench/export.py, offline: what the web app's runner reads from the engine."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pytest
import yaml

from gym import lock, undo
from gym.core import suites

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import agent_bench as ab  # noqa: E402
import export  # noqa: E402
import rows  # noqa: E402

NODES = {"items": [{"status": {"conditions": [{"type": "Ready", "status": "True"}]}},
                   {"status": {"conditions": [{"type": "Ready", "status": "False"}]}}]}


@pytest.fixture
def clusters(tmp_path, monkeypatch):
    """Two kubeconfigs, the lock and undo-log folders in tmp_path, docker and kubectl stubbed."""
    kdir = tmp_path / "kube"
    kdir.mkdir()
    for name in ("ai-gym", "ai-gym-2"):
        (kdir / name).write_text(yaml.safe_dump({"current-context": f"kind-{name}"}))
    monkeypatch.setattr(lock, "LOCK_DIR", tmp_path / "locks")
    monkeypatch.setattr(undo, "STATE_DIR", tmp_path / "state")
    nodes = {"ai-gym": {"items": NODES["items"][:1]}, "ai-gym-2": NODES}

    def quiet(cmd, timeout=20):
        if cmd[0] == "docker":
            return (0, "running\n") if cmd[-1] == "agent-box-ai-gym" else (1, "No such object")
        return 0, json.dumps(nodes[pathlib.Path(cmd[cmd.index("--kubeconfig") + 1]).name])
    monkeypatch.setattr(ab, "_quiet", quiet)
    yield kdir
    while lock._held:
        lock._held.pop().close()


def test_cluster_status(clusters):
    c = ab.cluster_status(clusters / "ai-gym")
    assert (c["context"], c["lock"], c["undo_logs"], c["nodes"], c["sandbox"]["state"], c["free"]) == \
        ("kind-ai-gym", None, [], {"ready": 1, "total": 1}, "running", True)
    c2 = ab.cluster_status(clusters / "ai-gym-2")
    assert c2["nodes"] == {"ready": 1, "total": 2} and c2["sandbox"]["state"] == "missing" and not c2["free"]


def test_a_busy_or_dirty_cluster_is_not_free(clusters):
    lock.hold_cluster("agent_bench run job j1", context="kind-ai-gym")
    c = ab.cluster_status(clusters / "ai-gym")
    assert c["lock"].startswith("agent_bench run job j1, pid") and not c["free"]
    lock._held.pop().close()
    (undo.STATE_DIR / "ai-gym").mkdir(parents=True)
    (undo.STATE_DIR / "ai-gym" / "cart-crash-001.json").write_text("[]")
    c = ab.cluster_status(clusters / "ai-gym")
    assert c["lock"] is None and c["undo_logs"] == ["cart-crash-001"] and not c["free"]


def test_status_json(clusters, capsys):
    ab.cmd_status({"models": [{"id": "m1"}]}, argparse.Namespace(json=True, kubeconfigs=str(clusters)))
    out = json.loads(capsys.readouterr().out)
    assert [c["name"] for c in out["clusters"]] == ["ai-gym", "ai-gym-2"] and out["models"] == ["m1"]
    assert out["engine"]["prompt_version"] == rows.PROMPT_VERSION
    lite = next(s for s in out["suites"] if s.get("name") == "lite")
    assert lite["runnable"] and lite["instances"] == len(suites.load("lite").instances)


def test_lock_holder_only_looks(tmp_path, monkeypatch):
    monkeypatch.setattr(lock, "LOCK_DIR", tmp_path)
    assert lock.holder("kind-x") is None
    lock.hold_cluster("validate_scenario", context="kind-x")
    assert lock.holder("kind-x").startswith("validate_scenario, pid")
    lock._held.pop().close()
    assert lock.holder("kind-x") is None
    assert lock.hold_cluster("agent_bench run", context="kind-x") == "kind-x"   # looking never kept it
    lock._held.pop().close()


def test_undo_pending_per_cluster(tmp_path, monkeypatch):
    monkeypatch.setattr(undo, "STATE_DIR", tmp_path)
    (tmp_path / "ai-gym-3").mkdir()
    (tmp_path / "ai-gym-3" / "x-001.json").write_text("[]")
    assert undo.pending("/home/u/.kube/gym/ai-gym-3") == ["x-001"] and undo.pending("/k/ai-gym") == []
    assert undo.cluster_key("/home/u/.kube/gym/ai-gym-3") == "ai-gym-3"


def test_axis_counts_and_tables_agree():
    rs = [{"model": "a", "status": "done", "passed": True, "tags": {"layer": "app", "fix_type": ["flag", "restart"]}},
          {"model": "a", "status": "done", "passed": False, "tags": {"layer": "k8s", "fix_type": ["flag"]}},
          {"model": "b", "status": "error", "passed": False, "tags": {"layer": "app"}}]
    counts = rows.axis_counts(rs, axes=("layer", "fix_type"))
    assert counts == {"layer": {"app": {"a": [1, 1]}, "k8s": {"a": [0, 1]}},
                      "fix_type": {"flag": {"a": [1, 2]}, "restart": {"a": [1, 1]}}}
    table = rows.axis_tables(rs, ["a", "b"], axes=("layer",))
    assert table[-2:] == ["| app | 1/1 (100%) | - |", "| k8s | 0/1 (0%) | - |"]


def test_export(tmp_path, monkeypatch):
    lite = suites.load("lite")
    monkeypatch.setattr(rows, "RESULTS", tmp_path)
    base = {"suite": "lite", "suite_version": lite.version, "hint_level": lite.hint_level,
            "prompt_version": rows.PROMPT_VERSION, "status": "done", "steps": 4, "tokens_in": 1_000_000,
            "tokens_out": 0}
    m0, m1 = lite.instances[:2]
    out = [{**base, "episode": "e1", "scenario": m0.id, "content_hash": m0.hash, "model": "opus", "attempt": 1,
            "passed": True, "clean": True, "safety": "clean", "tags": {"layer": "app"}, "ttd_s": 10, "ttm_s": 30},
           {**base, "episode": "e2", "scenario": m1.id, "content_hash": m1.hash, "model": "opus", "attempt": 1,
            "passed": False, "safety": "made_worse", "made_worse": ["x"], "tags": {"layer": "k8s"}},
           {**base, "episode": "e3", "scenario": m0.id, "content_hash": m0.hash, "model": "partner", "attempt": 1,
            "passed": True, "clean": True, "tags": {"layer": "app"}, "price": {"input": 2, "output": 0}},
           {**base, "episode": "e4", "scenario": m1.id, "content_hash": m1.hash, "model": "partner", "attempt": 1,
            "status": "error", "passed": False}]
    (tmp_path / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in out))
    (tmp_path / "judgments.jsonl").write_text(json.dumps({"judge": "j", "key": "e1", "root_cause": "correct"}) + "\n")
    (tmp_path / "oracle").mkdir()
    (tmp_path / "oracle" / "results.jsonl").write_text(json.dumps(
        {"scenario": m0.id, "content_hash": m0.hash, "model": "oracle", "attempt": 1, "status": "done", "fixed": True,
         "held": True}) + "\n")
    monkeypatch.setattr(export.scoreboard, "prices", lambda: {"opus": {"input": 1, "output": 1}})
    x = json.loads(json.dumps(export.build(lite)))   # JSON as the web app gets it
    assert (x["suite"]["name"], x["mode"], x["judge"], x["episodes"], x["models"]) == \
        ("lite", "fix", "j", 4, ["opus", "partner"])
    lb = {s["model"]: s for s in x["leaderboard"]}
    assert (lb["opus"]["passed"], lb["opus"]["episodes"], lb["opus"]["made_worse"]) == (1, 2, 1)
    assert (lb["partner"]["episodes"], lb["partner"]["errors_invalid"]) == (1, 1)
    sb = {s["model"]: s for s in x["scoreboard"]}
    assert (sb["opus"]["mitigated"], sb["opus"]["diagnosis_correct"], sb["opus"]["e2e"], sb["opus"]["cost_usd"]) == \
        (1, 1, 1, 2.0)
    assert sb["partner"]["cost_usd"] == 2.0 and sb["partner"]["judged"] == 0   # its own recorded price
    assert x["breakdowns"]["layer"]["app"] == {"opus": [1, 1], "partner": [1, 1]}
    assert x["calibration"]["suite"] == "lite" and len(x["catalog"]) == len(lite.instances)
    c0, c1 = x["catalog"][:2]
    assert c0["id"] == m0.id and c0["title"] and c0["prompt"] and c0["validation"]["status"] == "validated"
    assert (c0["oracle"], c1["oracle"]) == ("ok", None)
    diag = export.build(lite, mode="diagnose")
    assert diag["episodes"] == 0 and diag["leaderboard"] == [] and diag["calibration"] is None
    # leaderboard v1 = attempt 1 only: --max-attempt leaves later attempts out of every part
    with open(tmp_path / "results.jsonl", "a") as f:
        f.write(json.dumps({**out[0], "episode": "e5", "attempt": 2, "passed": False}) + "\n")
    every, first = export.build(lite), export.build(lite, max_attempt=1)
    assert (every["episodes"], first["episodes"], first["max_attempt"]) == (5, 4, 1)
    assert {s["model"]: s["episodes"] for s in first["leaderboard"]}["opus"] == 2
    n = {s["id"]: s["models"]["opus"]["n"] for s in first["calibration"]["scenarios"] if "opus" in s["models"]}
    assert n[m0.id] == 1
