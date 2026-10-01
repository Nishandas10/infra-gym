"""kubectl helpers shared by injectors, verifiers and the validation harness."""
from __future__ import annotations

import copy
import json
import subprocess
import time

APP_NS = "default"      # where the OpenTelemetry demo runs
GYM_NS = "gym-system"   # the gym's own helper pods


class KubeError(RuntimeError):
    pass


def run(*args, namespace=APP_NS, input=None, timeout=90):
    """Run kubectl and return the CompletedProcess (never raises on a non-zero exit)."""
    cmd = ["kubectl"]
    if namespace:
        cmd += ["-n", namespace]
    cmd += [str(a) for a in args]
    try:
        return subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise KubeError(f"timed out after {timeout}s: {' '.join(cmd)}") from e


def kubectl(*args, namespace=APP_NS, input=None, timeout=90):
    """Run kubectl, return stdout, raise KubeError on failure."""
    r = run(*args, namespace=namespace, input=input, timeout=timeout)
    if r.returncode != 0:
        raise KubeError(f"kubectl {' '.join(str(a) for a in args)}: {r.stderr.strip()}")
    return r.stdout


def get(kind, name=None, namespace=APP_NS, selector=None, missing_ok=False):
    args = ["get", kind] + ([name] if name else []) + (["-l", selector] if selector else []) + ["-o", "json"]
    r = run(*args, namespace=namespace)
    if r.returncode != 0:
        if missing_ok and "NotFound" in r.stderr:
            return None
        raise KubeError(f"kubectl {' '.join(args)}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def items(kind, namespace=APP_NS, selector=None):
    return get(kind, namespace=namespace, selector=selector)["items"]


def apply(manifest, namespace=APP_NS):
    """Apply one manifest dict or a list of them."""
    docs = manifest if isinstance(manifest, list) else [manifest]
    body = json.dumps({"apiVersion": "v1", "kind": "List", "items": docs})
    return kubectl("apply", "-f", "-", namespace=namespace, input=body)


def create(manifest, namespace=APP_NS):
    return kubectl("create", "-f", "-", namespace=namespace, input=json.dumps(manifest))


def delete(kind, name, namespace=APP_NS, wait=False, force=False):
    args = ["delete", kind, name, "--ignore-not-found", f"--wait={'true' if wait else 'false'}"]
    if force:
        args += ["--grace-period=0", "--force"]
    return kubectl(*args, namespace=namespace)


def patch(kind, name, body, patch_type="strategic", namespace=APP_NS):
    return kubectl("patch", kind, name, f"--type={patch_type}", "-p", json.dumps(body), namespace=namespace)


def exec_in(target, cmd, namespace=APP_NS, container=None, input=None, timeout=90):
    """kubectl exec into a pod or 'deploy/<name>'. Returns CompletedProcess."""
    args = ["exec"] + (["-i"] if input is not None else []) + [target]
    if container:
        args += ["-c", container]
    args += ["--"] + list(cmd)
    return run(*args, namespace=namespace, input=input, timeout=timeout)


def pods(selector, namespace=APP_NS):
    return items("pods", namespace=namespace, selector=selector)


def pod_ready(pod):
    if pod.get("metadata", {}).get("deletionTimestamp"):
        return False
    for c in pod.get("status", {}).get("conditions", []):
        if c.get("type") == "Ready":
            return c.get("status") == "True"
    return False


def restarts(pod):
    return sum(cs.get("restartCount", 0) for cs in pod.get("status", {}).get("containerStatuses", []))


def wait_until(fn, timeout, interval=5):
    """Call fn() until it returns something truthy or the timeout passes."""
    deadline = time.time() + timeout
    while True:
        value = fn()
        if value or time.time() >= deadline:
            return value
        time.sleep(interval)


def rollout_restart(kind, name, namespace=APP_NS):
    return kubectl("rollout", "restart", f"{kind}/{name}", namespace=namespace)


# ---------------------------------------------------------------- JSON pointers
def _tokens(pointer):
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer.lstrip("/").split("/")] if pointer else []


def pointer_get(obj, pointer):
    """Return (exists, value) for a JSON pointer such as /spec/template/spec."""
    cur = obj
    for tok in _tokens(pointer):
        if isinstance(cur, list):
            if not tok.isdigit() or int(tok) >= len(cur):
                return False, None
            cur = cur[int(tok)]
        elif isinstance(cur, dict):
            if tok not in cur:
                return False, None
            cur = cur[tok]
        else:
            return False, None
    return True, copy.deepcopy(cur)


def escape(key):
    """Escape a map key for use inside a JSON pointer (e.g. label keys with '/')."""
    return key.replace("~", "~0").replace("/", "~1")
