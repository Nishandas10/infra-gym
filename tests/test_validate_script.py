"""Scenario selection of scripts/validate_scenario.py: shards are disjoint and cover everything."""
from __future__ import annotations

import argparse

from scripts.validate_scenario import select


def args(**kw):
    base = dict(specs=[], all=False, eligible=True, split=None, hard_first=True, shard=None, suite=None)
    return argparse.Namespace(**{**base, **kw})


def test_shards_are_disjoint_and_complete():
    every = [s["id"] for s in select(args())]
    shards = [[s["id"] for s in select(args(shard=f"{i}/3"))] for i in (1, 2, 3)]
    assert sorted(sum(shards, [])) == sorted(every)
    assert len(set(sum(shards, []))) == len(every) == 83
    assert max(map(len, shards)) - min(map(len, shards)) <= 1
    hard = {s["id"] for s in select(args(split="hard"))}
    assert all(len(hard & set(shard)) >= 4 for shard in shards)   # Hard tier spread over every worker


def test_suite_selects_its_members():
    from gym.core import suites
    picked = [s["id"] for s in select(args(eligible=False, suite=["lite"]))]
    assert picked and set(picked) == {m.id for m in suites.load("lite").instances}
