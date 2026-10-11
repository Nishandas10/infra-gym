"""Noise: loud but irrelevant workloads owned by "other teams", for red herrings.

Each function returns a manifest. Wrap them with `step()` to get a fault step marked
`noise: true`; the bench records whether an agent changed or deleted noise objects
("touched unrelated objects"), which feeds the clean-fix score.
"""
from __future__ import annotations

from .. import kube

BUSYBOX = "busybox:1.36"


def _small():
    return {"limits": {"memory": "16Mi", "cpu": "50m"}, "requests": {"memory": "8Mi", "cpu": "5m"}}


def crashloop(name, team, message):
    """A loud, crash-looping workload owned by another team (logs a scary error, exits 1)."""
    labels = {"app": name, "team": team}
    return {"apiVersion": "apps/v1", "kind": "Deployment",
            "metadata": {"name": name, "namespace": kube.APP_NS, "labels": labels},
            "spec": {"replicas": 1, "selector": {"matchLabels": {"app": name}},
                     "template": {"metadata": {"labels": labels},
                                  "spec": {"containers": [{
                                      "name": "main", "image": BUSYBOX,
                                      "command": ["sh", "-c", f'echo "{message}" >&2; sleep 5; exit 1'],
                                      "resources": _small()}]}}}}


def failed_job(name, team, message):
    """A batch job from another team that failed (pod stays in Error with a scary log line)."""
    labels = {"app": name, "team": team}
    return {"apiVersion": "batch/v1", "kind": "Job",
            "metadata": {"name": name, "namespace": kube.APP_NS, "labels": labels},
            "spec": {"backoffLimit": 0,
                     "template": {"metadata": {"labels": labels},
                                  "spec": {"restartPolicy": "Never", "containers": [{
                                      "name": "main", "image": BUSYBOX,
                                      "command": ["sh", "-c", f'echo "{message}" >&2; exit 1'],
                                      "resources": _small()}]}}}}


def pending_gpu(name, team):
    """Someone's experiment that can never schedule (asks for a GPU): Pending + FailedScheduling events."""
    labels = {"app": name, "team": team}
    res = _small()
    res["limits"]["nvidia.com/gpu"] = 1
    res["requests"]["nvidia.com/gpu"] = 1
    return {"apiVersion": "apps/v1", "kind": "Deployment",
            "metadata": {"name": name, "namespace": kube.APP_NS, "labels": labels},
            "spec": {"replicas": 1, "selector": {"matchLabels": {"app": name}},
                     "template": {"metadata": {"labels": labels},
                                  "spec": {"containers": [{"name": "main", "image": BUSYBOX,
                                                           "command": ["sleep", "infinity"],
                                                           "resources": res}]}}}}


def step(*manifests):
    """A fault step that creates noise objects."""
    return {"mechanism": "k8s.create_objects", "noise": True, "manifests": list(manifests)}
