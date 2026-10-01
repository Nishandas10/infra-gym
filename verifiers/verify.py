"""Generic verifier (the referee): runs the checks listed in a scenario's spec.

Only outside evidence is used (see gym/checks.py). Exit code 0 = PASS
(healthy), 1 = FAIL.

usage: python verifiers/verify.py scenarios/<id>
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym import checks  # noqa: E402
from gym.spec import checks_of, load  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("spec_path")
    args = p.parse_args()
    spec, _ = load(args.spec_path)
    results = checks.run_checks(checks_of(spec))
    for c, status, msg in results:
        print(f"[{status:7s}] {checks.describe(c):32s} {msg}")
    overall = checks.overall(results)
    print(f"\nOVERALL: {'PASS - system healthy' if overall == checks.PASS else 'FAIL - system unhealthy'}")
    sys.exit(0 if overall == checks.PASS else 1)


if __name__ == "__main__":
    main()
