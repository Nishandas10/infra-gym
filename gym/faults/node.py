"""Faults on the nodes themselves (the kind node containers, reached from the gym's host with docker exec)."""
from __future__ import annotations

from .. import kube
from . import mechanism
from .k8s_objects import node_names


@mechanism("node.kubelet_stop", "node",
           "Stop the kubelet on a node: it goes NotReady and its pods are evicted after the toleration (5 min); "
           "revert starts it again. name: $worker (the first worker) or $workers")
def kubelet_stop(fault, undo, ctx):
    for node in node_names(fault["name"]):
        undo.add({"op": "hook", "hook": {"kubelet_start": node}})
        kube.node_exec(node, ["systemctl", "stop", "kubelet"])
