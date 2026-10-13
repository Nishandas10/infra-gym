"""Prove scenarios work end to end (see gym/harness.py for the steps).

usage:
  python scripts/validate_scenario.py scenarios/net-delay-002
  python scripts/validate_scenario.py scenarios/a scenarios/b ...
  python scripts/validate_scenario.py --all                    every scenario once
  python scripts/validate_scenario.py --eligible --repeat 5    every bench-eligible scenario 5 more times
  python scripts/validate_scenario.py --eligible --fill 5      top up to 5 runs of the current version
                                                                (skips quarantined ones; resumable)
  options: --split hard|train   only that tier;  --hard-first   Hard tier first
           --shard 2/3   only every 3rd scenario starting with the 2nd (one worker per cluster)

Parallel: one world per worker. Give each worker its own cluster and shard, e.g.
  KUBECONFIG=~/.kube/gym/ai-gym-2 python scripts/validate_scenario.py --eligible --fill 5 --shard 2/3
Stop gracefully with SIGTERM (kill <pid>): the current scenario finishes, then the worker exits.

Runs go round-robin (one pass over every scenario, then the next pass), so repeated runs of a
scenario are spread over time instead of back to back. Each result is appended to
results/validation.jsonl; the status (validated / quarantined / draft) is computed from those
results by gym/core/status.py and written into the instances by scripts/generate.py.
"""
import argparse
import os
import pathlib
import signal
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym import harness, toolbox  # noqa: E402
from gym.core import status  # noqa: E402
from gym.spec import all_specs, load  # noqa: E402

BROKEN_WORLD = ("ENV_UNHEALTHY", "RESTORE_FAILED", "ENV_CHANGED")
STOP = {"requested": False}


def request_stop(signum, frame):
    STOP["requested"] = True
    print("\nStop requested: finishing the current scenario, then exiting.", flush=True)


def select(args):
    paths = [str(s) for s in all_specs()] if (args.all or args.eligible or args.split) else args.specs
    specs = [load(p)[0] | {"_path": p} for p in paths]
    if args.eligible:
        specs = [s for s in specs if s["bench_eligible"]]
    if args.split:
        specs = [s for s in specs if s["split"] == args.split]
    if args.hard_first:
        specs.sort(key=lambda s: s["split"] != "hard")
    if args.shard:
        i, n = (int(x) for x in args.shard.split("/"))
        specs = specs[i - 1::n]
    return specs


def still_needed(spec, want, records):
    """Runs still needed to reach `want` runs of this version (0 once it is quarantined)."""
    st = status.of_spec(spec, records)
    return 0 if st.status == "quarantined" else max(0, want - st.runs)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("specs", nargs="*")
    p.add_argument("--all", action="store_true", help="every scenario")
    p.add_argument("--eligible", action="store_true", help="every bench-eligible scenario")
    p.add_argument("--split", choices=["hard", "train"], help="only this tier")
    p.add_argument("--hard-first", action="store_true", help="run the Hard tier first")
    p.add_argument("--shard", help="i/N: only this worker's share of the scenarios (disjoint across i)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--repeat", type=int, default=1, help="runs per scenario (default 1)")
    g.add_argument("--fill", type=int, help="top each scenario up to this many runs of its current version")
    p.add_argument("--keep-going", action="store_true",
                   help="continue even if a scenario leaves the cluster unhealthy")
    args = p.parse_args()
    specs = select(args)
    if not specs:
        p.error("give scenario paths, or --all / --eligible / --split")
    if args.shard and not os.environ.get("KUBECONFIG"):
        p.error("--shard needs its own KUBECONFIG (one cluster per worker): `kind create cluster` and others switch the "
                "default context, which would send this worker's commands to another world")
    signal.signal(signal.SIGTERM, request_stop)
    toolbox.ensure()
    verdicts = {s["id"]: [] for s in specs}
    passes = args.fill or args.repeat
    stop = False
    for n in range(passes):
        records = status.load_records()
        todo = [s for s in specs if (still_needed(s, args.fill, records) > 0 if args.fill else True)]
        if not todo:
            break
        print(f"\n##### pass {n + 1}/{passes}: {len(todo)} scenario(s)", flush=True)
        for s in todo:
            if STOP["requested"]:
                stop = True
                break
            rec = harness.validate(s["_path"])
            verdicts[rec["id"]].append(rec["verdict"])
            broken_world = rec["verdict"] in BROKEN_WORLD or \
                any("world not healthy" in x or "revert" in x.lower() for x in rec.get("notes", []))
            if broken_world and not args.keep_going:
                print(f"\nStopping: the cluster is not healthy after {rec['id']} ({rec['verdict']}). "
                      "Fix it (see results/logs/), then re-run; --fill resumes where this stopped.")
                stop = True
                break
        if stop:
            break
    records = status.load_records()
    print("\nSUMMARY (this run | status of the current version)")
    for s in specs:
        if verdicts[s["id"]]:
            st = status.of_spec(s, records)
            print(f"  {s['id']:48s} {' '.join(verdicts[s['id']]):40s} | {st.status} ({st.summary()})")
    print("\nRun python scripts/generate.py to write the new statuses into scenarios/ and CATALOG.md.")
    ran = [v for vs in verdicts.values() for v in vs]
    sys.exit(0 if ran and all(v == "VALIDATED" for v in ran) and not stop else 1)


if __name__ == "__main__":
    main()
