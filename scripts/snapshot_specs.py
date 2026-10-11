"""Record the behaviour-defining part of every scenario in tests/golden/specs.json.

usage:
  python scripts/snapshot_specs.py          # write the snapshot (only when a change is intended)

tests/test_spec_snapshot.py fails whenever a scenario's fault, checks, reference fix, validation
timings or prompt differ from this snapshot. Restructuring (schema v2, templates, generators)
must leave it passing; a deliberate behaviour change updates the snapshot in the same commit,
so the diff shows exactly which scenarios changed.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from gym.spec import all_specs, load  # noqa: E402

OUT = REPO / "tests" / "golden" / "specs.json"


def contract(spec):
    """The fields that decide what a scenario does and how it is judged."""
    return {
        "fault": spec["fault"],
        "checks": spec["verifier"]["checks"],
        "forbidden": spec["verifier"].get("forbidden", []),
        "solution": spec["solution"]["commands"],
        "validation": spec.get("validation") or {},
        "prompt": spec["task"]["prompt"],
        "budget": spec.get("budget") or {},
    }


def snapshot():
    out = {}
    for p in all_specs():
        spec, _ = load(p)
        out[spec["id"]] = contract(spec)
    return out


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot(), indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} ({len(snapshot())} scenarios)")


if __name__ == "__main__":
    main()
