"""On/off switch for any built-in OpenTelemetry Demo feature flag (Playbook step 3.18).

The Playbook version edits the flagd-config ConfigMap. In demo 3.x that has
no effect until flagd restarts, because flagd reads a copy made at pod start.
This version edits the live file (as the Feature Flags UI does) and confirms
flagd is serving the new value.

usage:
  python injectors/toggle_flag.py --list
  python injectors/toggle_flag.py paymentFailure --on            # 'on' or the largest failure variant
  python injectors/toggle_flag.py paymentFailure --variant 50%
  python injectors/toggle_flag.py paymentFailure --off
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym import kube  # noqa: E402
from gym.faults import flags  # noqa: E402


def pick_on_variant(variants):
    """'on' if the flag has it, else the strongest non-off variant (e.g. '100%', '10sec')."""
    if "on" in variants:
        return "on"
    others = [v for v in variants if v != "off"]
    return max(others, key=lambda v: float("".join(ch for ch in v if ch.isdigit() or ch == ".") or 0))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("flag", nargs="?")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--on", action="store_true")
    g.add_argument("--off", action="store_true")
    g.add_argument("--variant")
    g.add_argument("--list", action="store_true")
    args = p.parse_args()
    cfg = json.loads(flags.read_config())
    if args.list or not args.flag:
        for name, f in cfg["flags"].items():
            print(f"{name:32s} now={flags.evaluate(name).get('variant')!s:8s} variants={list(f['variants'])}")
        return
    if args.flag not in cfg["flags"]:
        sys.exit(f"Unknown flag '{args.flag}'. Known: {', '.join(cfg['flags'])}")
    variants = cfg["flags"][args.flag]["variants"]
    variant = "off" if args.off else (args.variant or pick_on_variant(variants))
    text = flags.read_config()
    flags.write_config(flags.set_variant(text, args.flag, variant))
    ctx = flags.targeting_context(text, args.flag)
    ok = kube.wait_until(lambda: flags.evaluate(args.flag, ctx).get("variant") == variant, timeout=30, interval=2)
    if not ok:
        sys.exit(f"flagd did not pick up {args.flag}={variant}: {flags.evaluate(args.flag, ctx)}")
    print(f"'{args.flag}' -> {variant} (flagd is serving it now)")


if __name__ == "__main__":
    main()
