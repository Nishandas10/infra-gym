"""Fault mechanisms, looked up by a spec's fault.type.

Each mechanism is a function f(fault, undo, ctx) that changes the live system
and records, in the undo log, how to put everything back.
"""
from __future__ import annotations

import dataclasses
import pathlib

from ..undo import UndoLog

REGISTRY = {}


@dataclasses.dataclass
class Context:
    scenario_id: str
    scenario_dir: pathlib.Path
    spec: dict


def mechanism(name, family, summary):
    def deco(fn):
        REGISTRY[name] = {"fn": fn, "family": family, "summary": summary}
        return fn
    return deco


def inject(spec, scenario_dir, force=False):
    undo = UndoLog(spec["id"])
    if undo.active and not force:
        raise RuntimeError(f"{spec['id']} is already injected; revert it first (or pass --force)")
    ftype = spec["fault"]["type"]
    if ftype not in REGISTRY:
        raise KeyError(f"unknown fault type {ftype!r}; known: {', '.join(sorted(REGISTRY))}")
    # Workloads to restart after everything else is reverted (e.g. Kafka consumers,
    # which can wedge after the broker comes back).
    for target in spec["fault"].get("restart_on_revert", []):
        undo.on_revert_restart(target)
    # Hooks run after the fault's own changes are undone, before those restarts.
    for hook in reversed(spec["fault"].get("revert_hooks", [])):
        undo.add({"op": "hook", "hook": hook})
    REGISTRY[ftype]["fn"](spec["fault"], undo, Context(spec["id"], pathlib.Path(scenario_dir), spec))
    return undo


def revert(spec):
    return UndoLog(spec["id"]).revert()


@mechanism("composite", "compound", "Several faults at once (each step is its own fault spec)")
def composite(fault, undo, ctx):
    import time
    for step in fault["steps"]:
        REGISTRY[step["type"]]["fn"](step, undo, ctx)
        time.sleep(step.get("pause_s", 0))


# Import mechanism modules so they register themselves.
from . import workload, chaos, flags, k8s_objects, runtime  # noqa: E402,F401
