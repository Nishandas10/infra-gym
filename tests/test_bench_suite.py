"""bench/agent_bench.py run --suite, offline: the cluster and the model are replaced by stubs."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pytest
import yaml

from gym.core import suites

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import agent_bench as ab  # noqa: E402
import rows  # noqa: E402

CFG = {"base_url": "http://model.invalid", "api_key_env": "UNUSED", "attempts_per_model": 1,
       "models": [{"id": "stub-model"}]}


class NoUndo:
    def __init__(self, sid):
        self.active = False


@pytest.fixture
def bench(tmp_path, monkeypatch):
    """agent_bench with results in tmp_path and every cluster or API call stubbed out."""
    played = []

    def play(sc, ms, client, cfg, row, state):
        played.append((sc["id"], row["hint_level"]))
        return {**row, "status": "done", "passed": True, "stop": "model_finished", "steps": 1}

    monkeypatch.setattr(rows, "RESULTS", tmp_path)
    monkeypatch.setattr(ab.toolbox, "ensure", lambda: None)
    monkeypatch.setattr(ab, "make_client", lambda ms: None)
    monkeypatch.setattr(ab, "ensure_world", lambda: [])
    monkeypatch.setattr(ab, "UndoLog", NoUndo)
    monkeypatch.setattr(ab.world, "snapshot", lambda: {})
    monkeypatch.setattr(ab, "_play", play)
    monkeypatch.setattr(ab, "_cleanup", lambda spec, snap, state: [])
    return played


def run(suite, **kw):
    args = argparse.Namespace(suite=suite, only=None, model=None, limit=None, retry_errors=False, rerun=False,
                              attempts=None, hint_level=None)
    for k, v in kw.items():
        setattr(args, k, v)
    cfg = dict(CFG, **({"hint_level": kw["hint_level"]} if kw.get("hint_level") else {}))
    ab.cmd_run(cfg, args)


def test_every_row_traces_to_the_suite_and_the_instance(bench, tmp_path):
    lite = suites.load("lite")
    run("lite", limit=3)
    out = rows.read_jsonl(tmp_path / "results.jsonl")
    assert len(out) == 3 and [b[0] for b in bench] == [m.id for m in lite.instances[:3]]
    hashes = {m.id: m.hash for m in lite.instances}
    for r in out:
        assert (r["suite"], r["suite_version"], r["suite_hash"]) == ("lite", lite.version, suites.fingerprint(lite))
        assert r["content_hash"] == hashes[r["scenario"]] and r["hint_level"] == lite.hint_level
        assert r["episode"] and r["validation_hash"].startswith("sha256:") and r["tags"]["layer"] and r["git_sha"]
    assert len(rows.load(lite)) == 3


def test_a_rerun_resumes_and_another_hint_level_is_a_new_episode(bench, tmp_path):
    run("lite", limit=2)
    run("lite", limit=2)
    assert len(bench) == 2                                   # nothing left to do the second time
    run("lite", limit=1, hint_level="ticket")
    assert bench[-1][1] == "ticket" and len(bench) == 3
    assert len(rows.load(suites.load("lite"))) == 2          # ticket episodes do not count for a page suite


def test_a_changed_instance_is_refused(bench, tmp_path):
    raw = yaml.safe_load((suites.SUITES / "lite.yaml").read_text())
    raw["instances"][0]["hash"] = "sha256:" + "0" * 64
    path = tmp_path / "lite.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(SystemExit, match="cannot run as frozen"):
        run(str(path))
    assert not bench


def test_private_suite_results_go_to_the_private_checkout(bench, tmp_path, monkeypatch):
    priv = tmp_path / "private"
    monkeypatch.setenv("INFRA_GYM_PRIVATE", str(priv))
    raw = yaml.safe_load((suites.SUITES / "lite.yaml").read_text())
    raw.update(name="secret", visibility="private")
    (priv / "suites").mkdir(parents=True)
    (priv / "suites" / "secret.yaml").write_text(yaml.safe_dump(raw))
    run("secret", limit=1)
    assert not (tmp_path / "results.jsonl").exists()
    assert json.loads((priv / "results" / "results.jsonl").read_text())["suite"] == "secret"


def test_rerun_repeats_only_the_named_scenarios(bench, tmp_path):
    lite = suites.load("lite")
    run("lite", limit=3)
    first, third = lite.instances[0].id, lite.instances[2].id
    run("lite", limit=3, rerun=True, only=f"{first},{third}")
    assert [b[0] for b in bench[3:]] == [first, third]
    assert len(rows.load(lite)) == 3                         # the newer row replaces the older one


def test_damage_counts_against_the_agent_only_if_it_changed_something():
    assert ab.attribute_damage(["journey:browse"], agent_changed=True) == (["journey:browse"], [])
    assert ab.attribute_damage(["journey:browse"], agent_changed=False) == ([], ["journey:browse"])
