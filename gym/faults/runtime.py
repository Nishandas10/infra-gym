"""Faults made inside running processes: datastore settings, database roles and
grants, Kafka topic configs... changed with the tools the software ships."""
from __future__ import annotations

import time

from .. import kube
from ..undo import restart
from . import mechanism


def _run(target, cmd, namespace, container=None, stdin=None):
    r = kube.exec_in(target, cmd, namespace=namespace, container=container, input=stdin, timeout=180)
    if r.returncode != 0:
        raise kube.KubeError(f"{' '.join(cmd)[:120]}: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


@mechanism("exec_commands", "runtime",
           "Run commands inside a pod (e.g. valkey-cli CONFIG SET, psql ALTER ROLE) with explicit undo commands")
def exec_commands(fault, undo, ctx):
    target = fault["target"]
    ns = fault.get("namespace", kube.APP_NS)
    container = fault.get("container")
    for target_restart in fault.get("restart_after", []):
        undo.on_revert_restart(target_restart, kube.APP_NS)
    # Undo commands run in reverse order, so record them reversed.
    for cmd in reversed(fault.get("undo_commands", [])):
        undo.on_revert_exec(target, cmd, namespace=ns, container=container)
    for cmd in fault["commands"]:
        _run(target, cmd, ns, container)
    for target_restart in fault.get("restart_after", []):
        time.sleep(fault.get("settle_s", 2))
        restart(target_restart, kube.APP_NS)
