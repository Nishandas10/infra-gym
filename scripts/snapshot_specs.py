"""Record the behaviour-defining part of every scenario in tests/golden/specs.json, and a fingerprint
of every fault mechanism's code in tests/golden/mechanisms.json.

usage:
  python scripts/snapshot_specs.py          # write the snapshot (only when a change is intended)

tests/test_spec_snapshot.py fails whenever a scenario's fault, checks, invariants, durability
restarts, forbidden actions, reference fix, validation timings, page prompt or budget differ from
this snapshot.
Restructuring must leave it passing; a deliberate behaviour change updates the snapshot in the
same commit, so the diff shows exactly which scenarios changed.

The snapshot keeps the spec-v1 shape it was first recorded in (fault.type / composite), so the
v1 -> v2 migration is checked against exactly what ran before it: `contract()` maps a v2
instance back to that shape.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from gym.faults import ALIASES  # noqa: E402
from gym.spec import all_specs, load  # noqa: E402

OUT = REPO / "tests" / "golden" / "specs.json"
MECH_OUT = REPO / "tests" / "golden" / "mechanisms.json"
V1_NAME = {new: old for old, new in ALIASES.items()}
FAULT_LEVEL = ("restart_on_revert", "revert_hooks")


def v1_fault(fault):
    # mechanisms added after the migration have no v1 name and keep their own
    steps = [{"type": V1_NAME.get(s["mechanism"], s["mechanism"]), **{k: v for k, v in s.items() if k != "mechanism"}}
             for s in fault["steps"]]
    top = {k: fault[k] for k in FAULT_LEVEL if fault.get(k) is not None}
    if len(steps) == 1:
        return {**steps[0], **top}
    return {"type": "composite", "steps": steps, **top}


def contract(spec):
    """The fields that decide what a scenario does and how it is judged."""
    return {
        "fault": v1_fault(spec["fault"]),
        "checks": spec["verifier"]["checks"],
        "invariants": spec["verifier"]["invariants"],
        "durability": spec["verifier"]["durability"],
        "forbidden": spec["verifier"]["forbidden"],
        "solution": spec["reference"]["commands"],
        "validation": spec["validation"],
        "prompt": spec["task"]["prompts"]["page"],
        "budget": spec["budget"],
        # false alarms only, so the entries of every other scenario keep their recorded shape
        **({"kind": "false_alarm", "alarm_checks": spec["verifier"]["alarm_checks"]}
           if spec["task"].get("kind") == "false_alarm" else {}),
    }


def snapshot():
    out = {}
    for p in all_specs():
        spec, _ = load(p)
        out[spec["id"]] = contract(spec)
    return out


def mechanism_fingerprints():
    """{mechanism: {version, module, source}}: source = sha256 of the module file the mechanism lives in, so a
    change to it or to a helper next to it shows up (tests/test_mechanism_fingerprints.py)."""
    import hashlib
    import inspect

    from gym import faults
    out = {}
    for name, m in sorted(faults.REGISTRY.items()):
        path = pathlib.Path(inspect.getsourcefile(m["fn"])).resolve()
        out[name] = {"version": m["version"], "module": str(path.relative_to(REPO)),
                     "source": hashlib.sha256(path.read_bytes()).hexdigest()[:16]}
    return out


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    snap = snapshot()
    OUT.write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} ({len(snap)} scenarios)")
    mech = mechanism_fingerprints()
    MECH_OUT.write_text(json.dumps(mech, indent=1, sort_keys=True) + "\n")
    print(f"wrote {MECH_OUT.relative_to(REPO)} ({len(mech)} mechanisms)")


if __name__ == "__main__":
    main()
