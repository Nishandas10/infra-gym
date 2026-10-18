"""Fault mechanisms, looked up by each fault step's `mechanism` name.

Each mechanism is a function f(step, undo, ctx) that changes the live system and records, in
the undo log, how to put everything back. A scenario's fault is a list of steps, injected in
order (with an optional `pause_s` after each).

Names are prefixed by what they act on: k8s.* (Kubernetes objects), app.* (the shop's own
feature flags), runtime.* (commands inside running pods), chaos.* (Chaos Mesh), node.* (the nodes themselves).
"""
from __future__ import annotations

import dataclasses
import pathlib
import time

from ..undo import UndoLog

REGISTRY = {}

# Spec v1 names (fault.type), still found in older results files (results/validation.jsonl
# "type", bench results "fault_type").
ALIASES = {
    "workload_patch": "k8s.workload_patch",
    "memory_limit_misconfig": "k8s.memory_limit",
    "object_patch": "k8s.object_patch",
    "configmap_edit": "k8s.configmap_edit",
    "create_objects": "k8s.create_objects",
    "delete_object": "k8s.delete_object",
    "pin_endpoints": "k8s.pin_endpoints",
    "exec_commands": "runtime.exec",
    "feature_flag": "app.flag",
    "flag_in_source_config": "app.flag_source_config",
    "chaos_mesh": "chaos.mesh",
}


@dataclasses.dataclass
class Context:
    scenario_id: str
    scenario_dir: pathlib.Path
    spec: dict


def mechanism(name, family, summary, version=1):
    """version: bump it when a code change alters what the mechanism does for scenarios that already use it.
    Above 1 it enters their validation_hash (gym/core/generate.py), so their old evidence stops counting.
    tests/test_mechanism_fingerprints.py fails on any code change until it is bumped or re-recorded."""
    def deco(fn):
        REGISTRY[name] = {"fn": fn, "family": family, "summary": summary, "version": version}
        return fn
    return deco


def canonical(name):
    """A mechanism's current name, also for v1 names found in old results."""
    return ALIASES.get(name, name)


def inject(spec, scenario_dir, force=False):
    undo = UndoLog(spec["id"])
    if undo.active and not force:
        raise RuntimeError(f"{spec['id']} is already injected; revert it first (or pass --force)")
    fault = spec["fault"]
    for step in fault["steps"]:
        if step["mechanism"] not in REGISTRY:
            raise KeyError(f"unknown mechanism {step['mechanism']!r}; known: {', '.join(sorted(REGISTRY))}")
    # Workloads to restart after everything else is reverted (e.g. Kafka consumers,
    # which can wedge after the broker comes back).
    for target in fault.get("restart_on_revert") or []:
        undo.on_revert_restart(target)
    # Hooks run after the fault's own changes are undone, before those restarts.
    for hook in reversed(fault.get("revert_hooks") or []):
        undo.add({"op": "hook", "hook": hook})
    ctx = Context(spec["id"], pathlib.Path(scenario_dir), spec)
    steps = fault["steps"]
    for step in steps:
        REGISTRY[step["mechanism"]]["fn"](step, undo, ctx)
        if len(steps) > 1:
            time.sleep(step.get("pause_s", 0))
    return undo


def revert(spec):
    return UndoLog(spec["id"]).revert()


# Import mechanism modules so they register themselves.
from . import workload, chaos, flags, k8s_objects, node, runtime  # noqa: E402,F401
