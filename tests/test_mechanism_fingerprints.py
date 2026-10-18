"""A fault mechanism's code cannot change silently (see scripts/snapshot_specs.py, mechanism_fingerprints).

Every scenario's evidence (validation runs, long holds, oracle) was gathered with the mechanisms' code as it was.
Hashes cover the scenario's own fields but not that code, so a change to a mechanism could alter what existing
scenarios do while their evidence keeps counting (hard-pinned-endpoints-108 had to become v2 through an opt-in
field for this reason). This test makes the change a decision.
"""
from __future__ import annotations

import json

from scripts.snapshot_specs import MECH_OUT, mechanism_fingerprints

GOLDEN = json.loads(MECH_OUT.read_text())
CURRENT = mechanism_fingerprints()


def test_mechanism_code_unchanged_or_versioned():
    changed = sorted(n for n in CURRENT if n in GOLDEN and CURRENT[n]["source"] != GOLDEN[n]["source"]
                     and CURRENT[n]["version"] == GOLDEN[n]["version"])
    modules = ", ".join(sorted({CURRENT[n]["module"] for n in changed}))
    assert not changed, (
        f"fault mechanism code changed: {', '.join(changed)} ({modules}).\n"
        "If it changes what scenarios already using it do: bump `version` in its @mechanism(...) (those instances get new\n"
        "hashes: re-validate them, refreeze suites holding them). If it does not (a refactor, a new opt-in field, another\n"
        "mechanism in the same module): re-record with `python scripts/snapshot_specs.py`.")


def test_every_mechanism_is_recorded():
    assert sorted(CURRENT) == sorted(GOLDEN), "a mechanism was added or removed: python scripts/snapshot_specs.py"


def test_only_a_bumped_version_enters_the_validation_hash(monkeypatch):
    from gym import faults
    from gym.core import generate
    from gym.spec import REPO, load
    spec, _ = load(REPO / "scenarios" / "hard-pinned-endpoints-108")
    before = generate.validation_hash(spec, {})
    assert generate.mechanism_versions(spec["fault"]) == {}        # every mechanism is at version 1 today
    monkeypatch.setitem(faults.REGISTRY, "k8s.pin_endpoints", {**faults.REGISTRY["k8s.pin_endpoints"], "version": 2})
    assert generate.mechanism_versions(spec["fault"]) == {"k8s.pin_endpoints": 2}
    assert generate.validation_hash(spec, {}) != before
