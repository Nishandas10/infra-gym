"""Run modes other than fix (agent_bench.py --mode).

  fix       the default: find the cause and fix it; graded by the scenario's verifier
  diagnose  the scenario's page prompt, but the agent must not change anything: it names the root cause
  detect    a routine health check with no symptom given: is anything wrong right now, and if so, where

Every scenario can be played in diagnose and detect, false alarms included (the right answer is then "no incident").
diagnose and detect end with a JSON answer that is graded here, without a judge: whether there is an incident,
and which object is at fault (`ground_truth.root_causes[].component`). The judge grades the explanation later.
Any change to the cluster fails a diagnose or detect episode, exactly as in a false alarm.

A scenario with task.kind diagnose has a fix the agent cannot make (the node itself, outside its permissions); it is
played in diagnose and detect only, never in fix.
"""
from __future__ import annotations

import json
import re

MODES = ("fix", "diagnose", "detect")
READONLY = ("diagnose", "detect")


def playable(spec, mode):
    """Whether a scenario can be played in this mode: a task.kind diagnose scenario only in the read-only modes."""
    return mode in READONLY or spec["task"].get("kind") != "diagnose"


# kubectl's short names and plurals -> the kind used in ground_truth components
KIND_ALIASES = {
    "deploy": "deployment", "deployments": "deployment", "deployment.apps": "deployment",
    "svc": "service", "services": "service", "cm": "configmap", "configmaps": "configmap",
    "sts": "statefulset", "statefulsets": "statefulset", "ds": "daemonset", "daemonsets": "daemonset",
    "no": "node", "nodes": "node", "netpol": "networkpolicy", "networkpolicies": "networkpolicy",
    "pvc": "persistentvolumeclaim", "persistentvolumeclaims": "persistentvolumeclaim",
    "sa": "serviceaccount", "serviceaccounts": "serviceaccount", "pods": "pod", "po": "pod",
    "quota": "resourcequota", "resourcequotas": "resourcequota", "limits": "limitrange", "limitranges": "limitrange",
    "secrets": "secret", "jobs": "job", "cronjobs": "cronjob", "cj": "cronjob", "flags": "flag",
    "featureflag": "flag", "feature-flag": "flag", "ep": "endpoints", "endpointslices": "endpointslice",
    "validatingwebhookconfigurations": "validatingwebhookconfiguration",
    "mutatingwebhookconfigurations": "mutatingwebhookconfiguration",
}
ANSWER_RE = re.compile(r"\{[^{}]*\"incident\"[^{}]*\}", re.S)


def last_reply(messages):
    """The full text of the agent's last reply (the stored diagnosis is truncated)."""
    return next((m.get("content") or "" for m in reversed(messages) if m.get("role") == "assistant"), "")


def parse_answer(text):
    """The last JSON object with an "incident" key in the reply, or None."""
    for blob in reversed(ANSWER_RE.findall(text or "")):
        try:
            answer = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(answer, dict):
            return answer
    return None


def _bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "yes"):
        return True
    if isinstance(v, str) and v.strip().lower() in ("false", "no"):
        return False
    return None


def norm_component(c):
    """'Deployment/payment', 'deploy/payment', 'default/deployment/payment' -> ('deployment', 'payment')."""
    parts = [p for p in str(c).strip().strip("`").lower().split("/") if p]
    if len(parts) < 2:
        return None
    kind, name = parts[-2], parts[-1]
    return KIND_ALIASES.get(kind, kind), name


def _matches(target, answer, workers):
    t, a = norm_component(target), norm_component(answer)
    if not t or not a:
        return False
    (tk, tn), (ak, an) = t, a
    if tn in ("$workers", "$worker"):
        return ak == "node" and (an in {w.lower() for w in workers} or an == tn)
    if (tk, tn) == (ak, an):
        return True
    # a pod of the faulty Deployment names the same thing
    return tk in ("deployment", "statefulset", "daemonset") and ak == "pod" and an.startswith(tn + "-")


def grade(spec, answer, workers=()):
    """Grade a diagnose/detect answer against the scenario's ground truth."""
    expected = spec["task"].get("kind") != "false_alarm"
    incident = _bool((answer or {}).get("incident"))
    out = {"answer": answer, "incident_ok": answer is not None and incident is expected, "component_ok": None,
           "expected_incident": expected}
    if expected:
        given = (answer or {}).get("component")
        given = given if isinstance(given, list) else [given] if given else []
        targets = [rc["component"] for rc in spec["ground_truth"]["root_causes"]]
        found = [t for t in targets if any(_matches(t, g, workers) for g in given)]
        out["component_ok"] = bool(found)
        out["root_causes_found"] = f"{len(found)}/{len(targets)}"
    out["correct"] = bool(out["incident_ok"] and (out["component_ok"] if expected else True))
    return out


def oracle_answer(spec):
    """What a perfect diagnosis says (the oracle agent's answer in diagnose/detect)."""
    false_alarm = spec["task"].get("kind") == "false_alarm"
    return {"incident": not false_alarm,
            "component": None if false_alarm else spec["ground_truth"]["root_causes"][0]["component"],
            "summary": spec["ground_truth"]["explanation"][:300]}
