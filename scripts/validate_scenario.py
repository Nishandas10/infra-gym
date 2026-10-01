"""Prove scenarios work end to end (see gym/harness.py for the steps).

usage:
  python scripts/validate_scenario.py scenarios/net-delay-002
  python scripts/validate_scenario.py scenarios/a scenarios/b ...
  python scripts/validate_scenario.py --all

Each result is appended to results/validation.jsonl.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym import harness, toolbox  # noqa: E402
from gym.spec import all_specs  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("specs", nargs="*")
    p.add_argument("--all", action="store_true")
    p.add_argument("--keep-going", action="store_true",
                   help="continue even if a scenario leaves the cluster unhealthy")
    args = p.parse_args()
    specs = [str(s) for s in all_specs()] if args.all else args.specs
    if not specs:
        p.error("give scenario paths or --all")
    toolbox.ensure()
    verdicts = {}
    for s in specs:
        rec = harness.validate(s)
        verdicts[rec["id"]] = rec["verdict"]
        broken_world = rec["verdict"] in ("ENV_UNHEALTHY", "RESTORE_FAILED") or \
            any("world not healthy" in n or "revert" in n.lower() for n in rec.get("notes", []))
        if broken_world and not args.keep_going:
            print(f"\nStopping: the cluster is not healthy after {rec['id']} ({rec['verdict']}). "
                  "Fix it (see results/logs/), then re-run the remaining scenarios.")
            break
    print("\nSUMMARY")
    for sid, verdict in verdicts.items():
        print(f"  {verdict:20s} {sid}")
    sys.exit(0 if all(v == "VALIDATED" for v in verdicts.values()) else 1)


if __name__ == "__main__":
    main()
