"""Scenario selection of scripts/validate_scenario.py: shards are disjoint and cover everything."""
from __future__ import annotations

import argparse

from scripts.validate_scenario import needs_long_hold, select


def args(**kw):
    base = dict(specs=[], all=False, eligible=True, split=None, hard_first=True, shard=None, suite=None)
    return argparse.Namespace(**{**base, **kw})


def test_shards_are_disjoint_and_complete():
    every = [s["id"] for s in select(args())]
    shards = [[s["id"] for s in select(args(shard=f"{i}/3"))] for i in (1, 2, 3)]
    assert sorted(sum(shards, [])) == sorted(every)
    assert len(set(sum(shards, []))) == len(every) >= 83   # 83 before Phase 7 added scenarios
    assert max(map(len, shards)) - min(map(len, shards)) <= 1
    hard = {s["id"] for s in select(args(split="hard"))}
    assert all(len(hard & set(shard)) >= 4 for shard in shards)   # Hard tier spread over every worker


def test_suite_selects_its_members():
    from gym.core import suites
    picked = [s["id"] for s in select(args(eligible=False, suite=["lite"]))]
    assert picked and set(picked) == {m.id for m in suites.load("lite").instances}


def test_long_hold_since_counts_only_newer_runs():
    spec = select(args(eligible=False, specs=["scenarios/hard-pinned-endpoints-108"]))[0]
    vh = spec["validation_hash"]
    run = {"validation_hash": vh, "verdict": "VALIDATED", "hold_mode": "normal", "started": "2026-10-01T10:00:00"}
    old_hold = {**run, "hold_mode": "long", "started": "2026-10-10T10:00:00"}
    records = {vh: [run] * 5 + [old_hold]}
    assert not needs_long_hold(spec, records)                                  # any passing long hold counts
    assert needs_long_hold(spec, records, since="2026-10-17T20:00:00")         # ... but not one from before the change
    records[vh].append({**old_hold, "started": "2026-10-18T05:00:00"})
    assert not needs_long_hold(spec, records, since="2026-10-17T20:00:00")
    records[vh].append({**old_hold, "verdict": "SELF_HEALED", "started": "2026-10-18T06:00:00"})
    assert needs_long_hold(spec, records, since="2026-10-18T05:30:00")         # a failed one does not count
