"""Generic injector: breaks the cluster the way a scenario's spec describes.

usage:
  python injectors/inject.py scenarios/<id>            # inject the fault
  python injectors/inject.py scenarios/<id> --revert   # undo it exactly

The mechanism is chosen by fault.type in spec.yaml (see gym/faults/). Every
injection records how to undo itself in .gym_state/<id>.json.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym import faults  # noqa: E402
from gym.spec import load  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("spec_path")
    p.add_argument("--revert", action="store_true", help="undo a previous injection")
    p.add_argument("--force", action="store_true", help="inject even if an undo log already exists")
    args = p.parse_args()
    spec, sdir = load(args.spec_path)
    if args.revert:
        errors = faults.revert(spec)
        if errors:
            sys.exit("Revert finished with errors:\n  " + "\n  ".join(errors))
        print(f"Reverted '{spec['id']}'.")
        return
    faults.inject(spec, sdir, force=args.force)
    print(f"Injected fault '{spec['id']}' ({spec['fault']['type']}).")
    print("Give it 20-60 seconds, then run: python verifiers/verify.py " + args.spec_path)


if __name__ == "__main__":
    main()
