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
    monkeypatch.setattr(ab, "refresh_sandbox", lambda: None)
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


# ------------------------------------------------------------------ what the agent is told
# sha256 of every text the agent can be shown, per rows.PROMPT_VERSION. A change to any of them changes every
# model's results: bump rows.PROMPT_VERSION, note it in bench/README.md, then pin the new hash here.
PROMPT_HASHES = {2: "afa36749f70617e4c15814b1523b5f7b900c02814a615924eb18f9175bbb24ec",
                 3: "4b6195ae219a43be926a8f8281707745af6d42bd6165d26f2615d2261f7bd60a"}


def test_prompt_texts_are_pinned_to_the_prompt_version():
    import hashlib
    texts = (ab.SYSTEM_PROMPT, ab.NUDGE_PROMPT, ab.BUDGET_NOTE, str(ab.BUDGET_WARNING_AT), ab.REPORT_PROMPT)
    if rows.PROMPT_VERSION >= 3:   # the diagnose/detect texts (bench/modes.py) came with version 3
        texts += (ab.READONLY_SYSTEM_PROMPT, *ab.MODE_TASKS.values(), ab.DETECT_PROMPT, ab.READONLY_NUDGE_PROMPT,
                  ab.READONLY_REPORT_PROMPT)
    got = hashlib.sha256("\x00".join(texts).encode()).hexdigest()
    assert got == PROMPT_HASHES.get(rows.PROMPT_VERSION), \
        f"agent prompt changed: bump rows.PROMPT_VERSION and pin {got}"


def test_system_prompt_states_the_command_budget():
    assert "at most 30 commands" in ab.system_prompt(30)


def test_budget_reminder_once_when_five_are_left():
    notes = {after: ab.budget_note(after - 1, after, 30) for after in range(1, 31)}
    assert [a for a, n in notes.items() if n] == [25] and notes[25] == "[5 of your 30 commands left]"
    assert ab.budget_note(23, 27, 30) == "[3 of your 30 commands left]"   # several commands in one turn
    assert ab.budget_note(29, 31, 30) == ""                                # budget used up: the report follows
    assert ab.budget_note(0, 1, 3) == ""                                   # short budgets get no reminder


def test_rows_of_an_older_prompt_are_run_again(bench, tmp_path):
    run("lite", limit=1)
    lines = [json.loads(x) for x in (tmp_path / "results.jsonl").read_text().splitlines()]
    assert lines[0]["prompt_version"] == rows.PROMPT_VERSION
    del lines[0]["prompt_version"]                                         # as recorded before prompt versions
    (tmp_path / "results.jsonl").write_text(json.dumps(lines[0]) + "\n")
    assert not rows.load(suites.load("lite"))
    run("lite", limit=1)
    assert len(bench) == 2 and len(rows.load(suites.load("lite"))) == 1


def test_key_and_pacing_can_be_set_for_one_run():
    ms = ab.model_settings(CFG, CFG["models"][0])
    args = argparse.Namespace(api_key_env="FREE_KEY", min_seconds_between_calls=7.0)
    out = ab.with_overrides(ms, args)
    assert (out["api_key_env"], out["pace_s"], out["id"]) == ("FREE_KEY", 7.0, ms["id"])
    assert ab.with_overrides(ms, argparse.Namespace()) == ms


def test_a_shard_plays_its_share_of_the_plan(bench, monkeypatch):
    monkeypatch.setenv("KUBECONFIG", "/tmp/kube-test")
    run("lite", limit=4, shard="1/2")
    lite = [m.id for m in suites.load("lite").instances[:4]]
    assert [b[0] for b in bench] == lite[0::2]


def test_shards_stay_disjoint_when_a_worker_starts_late(bench, monkeypatch):
    """Worker 2 finishes before worker 1 starts: worker 1 must still play only its own share, not re-split the rest."""
    monkeypatch.setenv("KUBECONFIG", "/tmp/kube-test")
    lite = [m.id for m in suites.load("lite").instances[:6]]
    run("lite", limit=6, shard="2/3")
    run("lite", limit=6, shard="1/3")
    assert [b[0] for b in bench] == lite[1::3] + lite[0::3]


def test_a_shard_needs_its_own_cluster(bench, monkeypatch):
    monkeypatch.delenv("KUBECONFIG", raising=False)
    with pytest.raises(SystemExit):
        run("lite", limit=2, shard="1/2")
    assert bench == []


def test_the_spend_cap_stops_the_run(bench, monkeypatch, tmp_path):
    def play(sc, ms, client, cfg, row, state):   # 1M fresh input tokens at $1/1M = $1 per episode
        bench.append((sc["id"], row["hint_level"]))
        return {**row, "status": "done", "passed": True, "stop": "model_finished", "steps": 1, "tokens_in": 1_000_000}
    monkeypatch.setattr(ab, "_play", play)
    cfg = dict(CFG, models=[{"id": "stub-model", "price": {"input": 1, "output": 1}}])
    args = argparse.Namespace(suite="lite", only=None, model=None, limit=4, retry_errors=False, rerun=False,
                              attempts=None, hint_level=None, max_cost=1.5)
    ab.cmd_run(cfg, args)
    assert len(bench) == 2                       # $1 after the first, $2 >= $1.50 after the second: stop


def test_the_spend_cap_needs_a_price(bench):
    args = argparse.Namespace(suite="lite", only=None, model=None, limit=1, retry_errors=False, rerun=False,
                              attempts=None, hint_level=None, max_cost=5.0)
    with pytest.raises(SystemExit):
        ab.cmd_run(CFG, args)
