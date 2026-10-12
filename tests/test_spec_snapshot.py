"""Every scenario still does exactly what tests/golden/specs.json recorded (see scripts/snapshot_specs.py)."""
from __future__ import annotations

import json

import pytest

from scripts.snapshot_specs import OUT, snapshot

GOLDEN = json.loads(OUT.read_text())
CURRENT = snapshot()


def test_same_scenarios():
    assert sorted(CURRENT) == sorted(GOLDEN)


@pytest.mark.parametrize("sid", sorted(GOLDEN))
def test_behaviour_unchanged(sid):
    assert sid in CURRENT, f"{sid} disappeared"
    assert set(CURRENT[sid]) == set(GOLDEN[sid]), f"{sid}: recorded fields differ (re-run scripts/snapshot_specs.py)"
    for field, want in GOLDEN[sid].items():
        assert CURRENT[sid][field] == want, f"{sid}: {field} changed"
