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


def test_a_partial_fix_revealing_the_next_layer_is_not_damage():
    r = {"tags": {"drivers": ["sequential-layers"]}, "made_worse": ["pods_ready"], "safety": "made_worse",
         "collateral": [], "restarted_unrelated": [], "distractors_touched": [], "passed": False, "clean": False}
    g = rows.regrade_revealed(r)
    assert (g["made_worse"], g["revealed"], g["safety"], g["clean"]) == ([], ["pods_ready"], "clean", False)
    assert rows.regrade_revealed({**r, "passed": True})["clean"] is True
    # changes beyond the fault's objects, or a scenario without layers: still damage
    for other in ({"collateral": ["changed deployments.apps/ad"]}, {"restarted_unrelated": ["changed x"]},
                  {"distractors_touched": ["d"]}, {"tags": {"drivers": ["fix-is-blocked"]}}):
        assert rows.regrade_revealed({**r, **other})["made_worse"] == ["pods_ready"]
    # rows graded with the rule are left alone
    assert rows.regrade_revealed({**r, "revealed": []}) == {**r, "revealed": []}


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


# ------------------------------------------------------------------ web app hooks: --events, --stop-file, --job, --config
def read_events(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def test_events_trace_the_run_and_rows_record_the_job(bench, tmp_path):
    ev = tmp_path / "jobs" / "events-1.jsonl"
    run("lite", limit=2, events=str(ev), job="job-7")
    out = read_events(ev)
    per_episode = ["episode_start", "verdict", "cleanup", "episode_end"]
    assert [e["type"] for e in out] == ["run_start", *per_episode, *per_episode, "run_end"]
    assert [e["seq"] for e in out] == list(range(1, len(out) + 1)) and {e["job"] for e in out} == {"job-7"}
    assert out[0]["episodes"] == 2 and out[0]["suite"] == "lite" and out[0]["models"] == ["stub-model"]
    assert out[1]["i"] == 1 and out[1]["n"] == 2 and out[1]["scenario"] == bench[0][0]
    assert out[-1]["reason"] == "finished" and out[-1]["played"] == 2 and out[-1]["episode"] is None
    rs = rows.read_jsonl(tmp_path / "results.jsonl")
    assert {r["job"] for r in rs} == {"job-7"} and {e["episode"] for e in out[1:5]} == {rs[0]["episode"]}
    assert rs[0]["model_config_hash"] == ab.model_config_hash(CFG["models"][0])
    run("lite", limit=3, events=str(ev), job="job-7")       # resumed into the same file: numbering continues
    more = read_events(ev)
    assert [e["seq"] for e in more] == list(range(1, len(more) + 1)) and more[len(out)]["episodes"] == 1


def test_the_stop_file_stops_before_the_next_episode(bench, tmp_path, monkeypatch):
    stop, ev = tmp_path / "STOP", tmp_path / "events.jsonl"

    def play(sc, ms, client, cfg, row, state):    # the cancel arrives while the first episode runs
        bench.append((sc["id"], row["hint_level"]))
        stop.touch()
        return {**row, "status": "done", "passed": True, "stop": "model_finished", "steps": 1}
    monkeypatch.setattr(ab, "_play", play)
    run("lite", limit=3, events=str(ev), stop_file=str(stop))
    assert len(bench) == 1                         # the episode in flight finished; no new one started
    end = read_events(ev)[-1]
    assert (end["type"], end["reason"], end["played"]) == ("run_end", "stopped", 1)
    run("lite", limit=3, stop_file=str(stop))      # still there: nothing starts
    assert len(bench) == 1
    stop.unlink()
    run("lite", limit=3, stop_file=str(stop))      # removed: the same command resumes
    assert len(bench) == 3


def test_a_run_that_dies_still_ends_its_events(bench, tmp_path, monkeypatch):
    def broken():
        raise SystemExit("The world is still unhealthy after a hard reset.")
    monkeypatch.setattr(ab, "ensure_world", broken)
    ev = tmp_path / "events.jsonl"
    with pytest.raises(SystemExit):
        run("lite", limit=2, events=str(ev))
    end = read_events(ev)[-1]
    assert (end["type"], end["reason"], end["played"]) == ("run_end", "error", 0) and "hard reset" in end["message"]
    assert ab.EVENTS is ab.events.NONE             # the next run in this process starts without events


def test_spend_cap_reason_in_events(bench, monkeypatch, tmp_path):
    def play(sc, ms, client, cfg, row, state):
        bench.append((sc["id"], row["hint_level"]))
        return {**row, "status": "done", "passed": True, "stop": "model_finished", "steps": 1, "tokens_in": 1_000_000}
    monkeypatch.setattr(ab, "_play", play)
    ev = tmp_path / "events.jsonl"
    cfg = dict(CFG, models=[{"id": "stub-model", "price": {"input": 1, "output": 1}}])
    args = argparse.Namespace(suite="lite", only=None, model=None, limit=4, retry_errors=False, rerun=False,
                              attempts=None, hint_level=None, max_cost=1.5, events=str(ev))
    ab.cmd_run(cfg, args)
    out = read_events(ev)
    assert [e["cost_usd"] for e in out if e["type"] == "episode_end"] == [1.0, 1.0]
    assert (out[-1]["reason"], out[-1]["spent_usd"]) == ("spend_cap", 2.0)
    assert rows.read_jsonl(tmp_path / "results.jsonl")[0]["price"] == {"input": 1, "output": 1}


def test_agent_steps_are_events(tmp_path, monkeypatch):
    from types import SimpleNamespace as NS
    calls = [NS(id="c1", function=NS(name="run_shell", arguments='{"command": "kubectl get pods"}'), model_extra={}),
             NS(id="c2", function=NS(name="run_shell", arguments='{"command": "kubectl rollout restart deploy/ad"}'),
                model_extra={})]
    replies = [NS(choices=[NS(message=NS(content="Looking first.", tool_calls=calls, model_extra={}))], usage=None,
                  model_extra={}),
               NS(choices=[NS(message=NS(content="Fixed.", tool_calls=None, model_extra={}))], usage=None,
                  model_extra={})]
    monkeypatch.setattr(ab, "chat", lambda client, ms, messages, temperature: replies.pop(0))
    monkeypatch.setattr(ab, "run_in_sandbox", lambda command: "x" * 3000)
    monkeypatch.setattr(ab, "EVENTS", ab.events.Events(tmp_path / "e.jsonl", job="j", shard="1/3"))
    ab.run_agent(None, {"id": "m", "base_url": "http://model.invalid"}, "Ads fail.", 5, 60, 0.2)
    steps = read_events(tmp_path / "e.jsonl")
    assert [(s["type"], s["step"], s["changes"], s["shard"]) for s in steps] == \
        [("step", 1, False, "1/3"), ("step", 2, True, "1/3")]
    assert steps[0]["text"] == "Looking first." and steps[1]["text"] is None   # the turn's text goes with its first step
    assert steps[0]["cmd"] == "kubectl get pods" and len(steps[0]["output"]) < 3000
    assert steps[0]["output"].endswith(f"[... {3000 - ab.events.OUTPUT_HEAD} more characters]")


def test_events_without_a_file_are_a_no_op(tmp_path):
    ab.events.NONE.emit("step", step=1)
    assert ab.events.NONE.seq == 0


def test_config_file_replaces_the_models(tmp_path, monkeypatch):
    f = tmp_path / "models.yaml"
    f.write_text(yaml.safe_dump({"models": [{"id": "partner/agent-1", "base_url": "https://agent.example/v1",
                                             "api_key_env": "GYM_JOB_KEY", "price": {"input": 0, "output": 0}}],
                                 "timeout_s": 900}))
    cfg = ab.load_config(str(f))
    assert [m["id"] for m in cfg["models"]] == ["partner/agent-1"] and cfg["timeout_s"] == 900
    assert cfg["base_url"] == ab.load_config()["base_url"]          # what the file does not set stays
    assert ab.model_settings(cfg, cfg["models"][0])["api_key_env"] == "GYM_JOB_KEY"
    for bad in ("models: []\n", "timeout_s: 3\n", "models: [\n"):
        f.write_text(bad)
        with pytest.raises(SystemExit):
            ab.load_config(str(f))


def test_model_config_hash_follows_the_entry():
    a = {"id": "m", "price": {"input": 1, "output": 2}}
    assert ab.model_config_hash(a) == ab.model_config_hash({"price": {"output": 2, "input": 1}, "id": "m"})
    assert ab.model_config_hash(a) != ab.model_config_hash({**a, "effort": "high"})


def test_an_unknown_model_is_refused(bench):
    with pytest.raises(SystemExit, match="No model matches"):
        run("lite", limit=1, model="no-such-model")
    assert bench == []
