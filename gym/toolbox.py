"""Helper pods in the gym-system namespace.

gym-probe        runs gym/probe_script.py to exercise user journeys through the
                 shop's front door, plus raw HTTP calls to in-cluster APIs.
gym-kafka-tools  runs Kafka admin CLIs with a small heap. The broker container
                 has KAFKA_HEAP_OPTS=-Xms400M, so running the CLIs inside it
                 can push the broker past its memory limit.
gym-node-probe   a DaemonSet: one tiny pod per worker node, so a check can test a
                 connection from every node (faults that only some nodes see).
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from . import kube

PROBE_IMAGE = "python:3.12-alpine"
KAFKA_IMAGE = "ghcr.io/open-telemetry/demo:3.1.0-kafka"
NODE_PROBE = "gym-node-probe"
NODE_PROBE_IMAGE = "busybox:1.36"
_PROBE_SRC = pathlib.Path(__file__).with_name("probe_script.py")
_KEEP_ALIVE = ["sh", "-c", "trap 'exit 0' TERM INT; while true; do sleep 3600 & wait $!; done"]
# Above every shop pod and below the system classes, so a scenario that preempts pods (scheduling/priority-preemption)
# never takes the verifier's probes with it. preemptionPolicy Never: the gym's pods never preempt shop pods either.
PRIORITY_CLASS = "gym-critical"


def _deployment(name, image, env=None, limit="64Mi", volumes=None, mounts=None, annotations=None):
    return {
        "apiVersion": "apps/v1", "kind": "Deployment",
        "metadata": {"name": name, "namespace": kube.GYM_NS, "labels": {"app": name}},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": {"app": name}, "annotations": annotations or {}},
                "spec": {
                    "priorityClassName": PRIORITY_CLASS,
                    "terminationGracePeriodSeconds": 2,
                    # Services advertise short names (e.g. Kafka advertises "kafka:9092"),
                    # so let short names resolve as they would inside the app namespace.
                    "dnsConfig": {"searches": [f"{kube.APP_NS}.svc.cluster.local"]},
                    "containers": [{
                        "name": name, "image": image, "command": _KEEP_ALIVE,
                        "env": env or [],
                        "resources": {"requests": {"memory": "16Mi"}, "limits": {"memory": limit}},
                        "volumeMounts": mounts or [],
                    }],
                    "volumes": volumes or [],
                },
            },
        },
    }


def _node_probe():
    """No tolerations: it runs on the worker nodes only, like the shop's own pods."""
    labels = {"app": NODE_PROBE}
    return {
        "apiVersion": "apps/v1", "kind": "DaemonSet",
        "metadata": {"name": NODE_PROBE, "namespace": kube.GYM_NS, "labels": labels},
        "spec": {
            "selector": {"matchLabels": labels},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "priorityClassName": PRIORITY_CLASS,
                    "terminationGracePeriodSeconds": 2,
                    "containers": [{
                        "name": NODE_PROBE, "image": NODE_PROBE_IMAGE, "command": _KEEP_ALIVE,
                        "resources": {"requests": {"memory": "4Mi", "cpu": "5m"}, "limits": {"memory": "16Mi"}},
                    }],
                },
            },
        },
    }


def manifests():
    src = _PROBE_SRC.read_text()
    digest = hashlib.sha256(src.encode()).hexdigest()[:12]
    return [
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": kube.GYM_NS}},
        {"apiVersion": "scheduling.k8s.io/v1", "kind": "PriorityClass", "metadata": {"name": PRIORITY_CLASS},
         "value": 1000000000, "preemptionPolicy": "Never", "globalDefault": False,
         "description": "infra-gym helper pods (verifier probes); never preempted by scenario workloads"},
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": "gym-probe-script", "namespace": kube.GYM_NS},
         "data": {"probe.py": src}},
        _deployment("gym-probe", PROBE_IMAGE, limit="96Mi",
                    volumes=[{"name": "script", "configMap": {"name": "gym-probe-script"}}],
                    mounts=[{"name": "script", "mountPath": "/probe"}],
                    annotations={"gym/script-sha": digest}),
        _deployment("gym-kafka-tools", KAFKA_IMAGE, limit="320Mi",
                    env=[{"name": "KAFKA_HEAP_OPTS", "value": "-Xmx128M -Xms32M"},
                         # the image bundles an OpenTelemetry Java agent; keep the CLIs quiet
                         {"name": "OTEL_JAVAAGENT_ENABLED", "value": "false"},
                         {"name": "OTEL_SDK_DISABLED", "value": "true"}]),
        _node_probe(),
    ]


def ensure(timeout=300):
    """Create/refresh the helper pods and wait until they are Ready."""
    kube.apply(manifests(), namespace=kube.GYM_NS)
    for app in ("gym-probe", "gym-kafka-tools"):
        kube.kubectl("rollout", "status", f"deploy/{app}", f"--timeout={timeout}s", namespace=kube.GYM_NS,
                     timeout=timeout + 30)
    kube.kubectl("rollout", "status", f"ds/{NODE_PROBE}", f"--timeout={timeout}s", namespace=kube.GYM_NS,
                 timeout=timeout + 30)


def _pod(app):
    for p in kube.pods(f"app={app}", namespace=kube.GYM_NS):
        if kube.pod_ready(p):
            return p["metadata"]["name"]
    raise kube.KubeError(f"no ready {app} pod in {kube.GYM_NS} (run: python scripts/gym_setup.py)")


def node_probes():
    """{node name: ready gym-node-probe pod on it}."""
    return {p["spec"]["nodeName"]: p["metadata"]["name"]
            for p in kube.pods(f"app={NODE_PROBE}", namespace=kube.GYM_NS) if kube.pod_ready(p)}


def probe(plan, timeout=240):
    """Run the probe script with a plan dict; returns its JSON result."""
    plan = {"namespace": kube.APP_NS, **plan}
    r = kube.exec_in(_pod("gym-probe"), ["python3", "/probe/probe.py", json.dumps(plan)],
                     namespace=kube.GYM_NS, timeout=timeout)
    if r.returncode != 0:
        raise kube.KubeError(f"probe failed: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def http(url, method="GET", body=None, timeout=10):
    """One raw HTTP call from inside the cluster. Returns {'status','ms','body'}."""
    return probe({"raw": [{"name": "r", "method": method, "url": url, "body": body, "timeout": timeout}]},
                 timeout=timeout + 60)["r"]


def kafka(tool, *args, timeout=150):
    """Run a Kafka CLI (e.g. kafka('kafka-topics.sh', '--list')) against kafka:9092."""
    cmd = [f"/opt/kafka/bin/{tool}", "--bootstrap-server", f"kafka.{kube.APP_NS}.svc.cluster.local:9092", *args]
    return kube.exec_in(_pod("gym-kafka-tools"), cmd, namespace=kube.GYM_NS, timeout=timeout)
