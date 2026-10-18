"""Suites (gym/core/suites.py), suite selection (scripts/make_suite.py) and suite-scoped results (bench/rows.py)."""
from __future__ import annotations

import collections
import importlib.util
import pathlib
import sys

import pytest
import yaml
from pydantic import ValidationError

from gym.core import status, suites
from gym.core.schema import Suite

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import rows  # noqa: E402

_spec = importlib.util.spec_from_file_location("make_suite", REPO / "scripts" / "make_suite.py")
make_suite = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_suite)

INSTS = suites.instances()
RECORDS = status.load_records()
H = "sha256:" + "a" * 64


def suite(members, **kw):
    return Suite.model_validate({"name": "t", "version": 1, "visibility": "public",
                                 "instances": [{"id": i, "hash": h} for i, h in members], **kw})


def current(sid):
    return INSTS[sid][0]["content_hash"]


# ------------------------------------------------------------------ committed suites
PUBLIC = sorted(suites.SUITES.glob("*.yaml"))


@pytest.mark.parametrize("path", PUBLIC, ids=[p.stem for p in PUBLIC])
def test_committed_suite_matches_the_current_instances(path):
    s = suites.load(path)
    assert s.visibility == "public", "private suites must not be committed to this repo"
    assert not suites.verify(s, INSTS, RECORDS), "a member changed: freeze a new suite version"


def test_expected_public_suites_exist():
    assert {"bench-v1-dev", "hard-v1", "lite"} <= {p.stem for p in PUBLIC}


# Hard-tier scenarios added after hard-v1 was frozen; `make_suite.py --refreeze` before Phase 6 takes them in, and
# then this set is emptied again.
HARD_SINCE_FREEZE = {"hard-job-sidecar-never-completes-127"}


def test_hard_suite_is_the_whole_hard_tier():
    hard = {sid for sid, (spec, _) in INSTS.items() if spec["split"] == "hard" and spec["bench_eligible"]}
    members = {m.id for m in suites.load("hard-v1").instances}
    assert members <= hard
    assert hard - members == HARD_SINCE_FREEZE


def test_lite_members_never_failed_validation():
    for m in suites.load("lite").instances:
        assert status.of_spec(INSTS[m.id][0], RECORDS).failures == 0, m.id


PRIVATE_TEST = suites.private_root() / "suites" / "bench-v1-test.yaml"


@pytest.mark.skipif(not PRIVATE_TEST.exists(), reason="no private checkout (private/suites/bench-v1-test.yaml)")
def test_private_test_suite_rules():
    test = suites.load("bench-v1-test")
    assert test.visibility == "private"
    assert not suites.verify(test, INSTS, RECORDS)
    specs = [INSTS[m.id][0] for m in test.instances]
    assert all(status.of_spec(s, RECORDS).failures == 0 for s in specs), "the test suite admits only 5/5 instances"
    assert sum("flag" in s["tags"]["fix_type"] for s in specs) <= 4
    held_out = {m.id for m in test.instances}
    for name in ("bench-v1-dev", "lite"):
        assert not held_out & {m.id for m in suites.load(name).instances}, f"{name} overlaps the test suite"


# ------------------------------------------------------------------ schema and verify
def test_schema_rejects_duplicates_and_bad_hashes():
    with pytest.raises(ValidationError, match="more than once"):
        suite([("a-001", H), ("a-001", H)])
    with pytest.raises(ValidationError, match="sha256"):
        suite([("a-001", "abc")])


def evidence(sid, long_hold=True):
    """Five VALIDATED runs of the instance's current version, the last one a long hold if asked."""
    vhash = INSTS[sid][0]["validation_hash"]
    runs = [{"id": sid, "validation_hash": vhash, "verdict": "VALIDATED", "hold_mode": "normal"} for _ in range(5)]
    runs[-1]["hold_mode"] = "long" if long_hold else "normal"
    return {vhash: runs}


def test_verify_reports_each_problem():
    sid = "wl-listen-port-drift-014"
    ok = evidence(sid)
    assert not suites.verify(suite([(sid, current(sid))]), INSTS, ok)
    kinds = [p.kind for p in suites.verify(suite([(sid, H), ("no-such-thing-999", H)]), INSTS, ok)]
    assert kinds == ["hash", "missing"]
    chaos = next(i for i, (s, _) in INSTS.items() if not s["bench_eligible"])
    assert [p.kind for p in suites.verify(suite([(chaos, current(chaos))]), INSTS, ok)] == ["not_eligible"]
    assert [p.kind for p in suites.verify(suite([(sid, current(sid))]), INSTS, {})] == ["not_validated"]
    short = evidence(sid, long_hold=False)
    assert [p.kind for p in suites.verify(suite([(sid, current(sid))]), INSTS, short)] == ["no_long_hold"]


def test_private_suite_inside_the_public_folder_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(suites, "SUITES", tmp_path)
    (tmp_path / "t.yaml").write_text(f"name: t\nversion: 1\nvisibility: private\ninstances:\n- {{id: x-001, hash: '{H}'}}\n")
    with pytest.raises(ValueError, match="must not live in the public repo"):
        suites.load(tmp_path / "t.yaml")


def test_find_by_name_and_reject_set_files():
    assert suites.find("hard-v1") == suites.SUITES / "hard-v1.yaml"
    with pytest.raises(ValueError, match="replaced by suites"):
        suites.find("bench/sets/hard.txt")


def test_fingerprint_follows_members_and_hint_level():
    a = suite([("a-001", H)])
    assert suites.fingerprint(a) == suites.fingerprint(suite([("a-001", H)]))
    assert suites.fingerprint(a) != suites.fingerprint(suite([("a-001", "sha256:" + "b" * 64)]))
    assert suites.fingerprint(a) != suites.fingerprint(suite([("a-001", H)], hint_level="ticket"))


# ------------------------------------------------------------------ selection
def fake(sid, layer, fix=("config-edit",), symptom="hard-errors", seconds=100):
    return {"id": sid, "seconds": seconds,
            "spec": {"tags": {"layer": layer, "fix_type": list(fix), "symptom": symptom, "drivers": []}}}


POOL = ([fake(f"wl-{i:03d}", "workload") for i in range(12)] +
        [fake(f"app-{i:03d}", "app", fix=("flag",)) for i in range(8)] +
        [fake(f"ds-{i:03d}", "datastore", symptom="silent-data", seconds=50 + i) for i in range(4)])


def test_quotas_are_proportional_and_cover_every_group():
    q = make_suite.quotas({"a": 12, "b": 8, "c": 4, "d": 1}, 10)
    assert sum(q.values()) == 10 and min(q.values()) >= 1 and q["a"] > q["b"] > q["c"]


def test_select_is_seeded_balanced_and_capped():
    picked, quota = make_suite.select(POOL, 12, "layer", {("fix_type", "flag"): 2}, 7, False)
    again, _ = make_suite.select(POOL, 12, "layer", {("fix_type", "flag"): 2}, 7, False)
    assert [c["id"] for c in picked] == [c["id"] for c in again]
    by_layer = collections.Counter(c["spec"]["tags"]["layer"] for c in picked)
    assert len(picked) == 12 and by_layer["app"] == 2           # capped below its share of 4
    assert by_layer["workload"] == quota["workload"] + 2        # the cap's slots went to the largest open group
    other, _ = make_suite.select(POOL, 12, "layer", {("fix_type", "flag"): 2}, 8, False)
    assert {c["id"] for c in other} != {c["id"] for c in picked}


def test_select_fastest_takes_the_shortest_episodes():
    picked, _ = make_suite.select([c for c in POOL if c["spec"]["tags"]["layer"] == "datastore"], 2,
                                  "layer", {}, 1, True)
    assert [c["id"] for c in picked] == ["ds-000", "ds-001"]


def test_candidates_exclude_and_clean():
    cands = make_suite.candidates(INSTS, RECORDS, "train", False, set())
    ids = {c["id"] for c in cands}
    assert ids and all(INSTS[i][0]["split"] == "train" and INSTS[i][0]["bench_eligible"] for i in ids)
    clean = make_suite.candidates(INSTS, RECORDS, "train", True, {"wl-listen-port-drift-014"})
    assert all(c["status"].failures == 0 for c in clean) and "wl-listen-port-drift-014" not in {c["id"] for c in clean}


# ------------------------------------------------------------------ results scoped to a suite
def test_rows_count_only_the_suites_exact_instances():
    s = suite([("a-001", H)])
    pv = rows.PROMPT_VERSION
    rs = [{"scenario": "a-001", "model": "m", "attempt": 1, "content_hash": H, "hint_level": "page", "prompt_version": pv,
           "n": 1},
          {"scenario": "a-001", "model": "m", "attempt": 1, "content_hash": H, "hint_level": "page", "prompt_version": pv,
           "n": 2},
          {"scenario": "a-001", "model": "m", "attempt": 1, "content_hash": "sha256:" + "b" * 64, "n": 3},
          {"scenario": "a-001", "model": "m", "attempt": 1, "content_hash": H, "hint_level": "ticket", "n": 4},
          {"scenario": "a-001", "model": "m", "attempt": 1, "n": 5},       # from before suites
          {"scenario": "a-001", "model": "m", "attempt": 1, "content_hash": H, "hint_level": "page", "n": 6}]  # prompt v1
    latest = rows.latest(rs)
    assert [r["n"] for r in rows.in_suite(latest, s)] == [2]               # the re-run replaced the first
    assert sorted(r["n"] for r in rows.in_suite(latest, s, any_version=True)) == [2, 3, 4, 5, 6]


def test_private_results_stay_out_of_the_public_folder():
    priv = suite([("a-001", H)], visibility="private")
    assert rows.results_dir(priv) == suites.private_root() / "results"
    assert rows.results_dir(suite([("a-001", H)])) == rows.RESULTS


def test_refreeze_keeps_the_members_and_takes_their_current_hashes(tmp_path, monkeypatch):
    lite = suites.load("lite")
    raw = yaml.safe_load((suites.SUITES / "lite.yaml").read_text())
    stale = raw["instances"][0]["id"]
    raw["instances"][0]["hash"] = H
    (tmp_path / "lite.yaml").write_text(yaml.safe_dump(raw))
    records = {}
    for m in lite.instances:
        records.update(evidence(m.id))
    monkeypatch.setattr(make_suite.status, "load_records", lambda: records)
    make_suite.refreeze(str(tmp_path / "lite.yaml"))
    new = suites.load(tmp_path / "lite.yaml")
    assert new.version == lite.version + 1 and [m.id for m in new.instances] == [m.id for m in lite.instances]
    assert all(m.hash == current(m.id) for m in new.instances)
    assert new.selection["changed"] == [stale] and new.selection["refrozen_from"] == lite.version


def test_refreeze_refuses_a_member_that_no_longer_qualifies(tmp_path, monkeypatch):
    raw = yaml.safe_load((suites.SUITES / "lite.yaml").read_text())
    raw["instances"][0]["hash"] = H
    (tmp_path / "lite.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.setattr(make_suite.status, "load_records", lambda: {})      # nothing validated
    with pytest.raises(SystemExit, match="do not qualify"):
        make_suite.refreeze(str(tmp_path / "lite.yaml"))
