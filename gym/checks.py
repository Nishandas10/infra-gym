"""Verifier checks: outside evidence only.

Every check looks at the real system: the Kubernetes API, real user journeys
through the shop's front door (via the gym-probe pod), Kafka consumer lag, the
telemetry backends, the database. No check reads the injected fault or asks
the agent. That is what makes the verifier hard to cheat.

A scenario's spec lists its checks under verifier.checks, for example:
  - {type: journey, journey: cart, repeat: 3, max_error_pct: 0, max_avg_ms: 2500}
  - {type: pods_ready, selector: opentelemetry.io/name=cart}
"""
from __future__ import annotations

import json
import re
import statistics
import time

from . import kube, toolbox

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"

# What "the whole shop is healthy" means; used before injecting and after restoring.
# The Kafka lag checks catch a consumer that is Running but wedged (it happened:
# accounting stopped consuming after the broker flapped, with no restart).
WORLD_HEALTHY = [
    {"type": "pods_ready", "selector": "", "namespace": kube.APP_NS},
    {"type": "journey", "journey": "browse", "repeat": 2},
    {"type": "journey", "journey": "recommendations", "repeat": 2},
    {"type": "journey", "journey": "cart", "repeat": 2},
    {"type": "journey", "journey": "checkout", "repeat": 2},
    {"type": "kafka_lag", "group": "accounting", "max_lag": 200},
    {"type": "kafka_lag", "group": "fraud-detection", "max_lag": 200},
]

# Checks every fix must leave passing, besides the scenario's own (spec verifier.invariants).
# shop_health = every user journey of WORLD_HEALTHY: a fix that repairs the faulted journey but
# breaks another one fails. Namespace-wide pod readiness is left out on purpose: some scenarios
# leave broken decoy workloads in place, and those are not the fix's job.
INVARIANTS = {
    "shop_health": [c for c in WORLD_HEALTHY if c["type"] == "journey"],
}


def invariant_checks(spec):
    return [c for name in spec["verifier"]["invariants"] for c in INVARIANTS[name]]


# ------------------------------------------------------------------ pod state
def _pod_problem(p):
    st = p.get("status", {})
    for cs in st.get("initContainerStatuses", []) + st.get("containerStatuses", []):
        w = cs.get("state", {}).get("waiting")
        if w:
            return f"{cs['name']}: {w.get('reason')}"
        t = cs.get("lastState", {}).get("terminated")
        if t and not cs.get("ready") and t.get("reason"):
            return f"{cs['name']}: last exit {t.get('reason')}"
    for c in st.get("conditions", []):
        if c.get("type") == "PodScheduled" and c.get("status") == "False":
            return f"Pending: {c.get('reason')} {c.get('message', '')[:90]}"
    return st.get("phase", "?")


def _live(pods):
    """Pods that are meant to be running: not terminating, not finished, not evicted leftovers."""
    return [p for p in pods if not p["metadata"].get("deletionTimestamp")
            and p.get("status", {}).get("phase") not in ("Succeeded", "Failed")]


def c_pods_ready(selector="", namespace=kube.APP_NS, min_ready=1, exclude=(), **_):
    """exclude: workload names whose pods are left out (a fault's own decoys, which may crash-loop by design)."""
    pods = [p for p in _live(kube.pods(selector, namespace=namespace))
            if not any(p["metadata"]["name"].startswith(f"{n}-") for n in exclude)]
    ready = [p for p in pods if kube.pod_ready(p)]
    bad = [f"{p['metadata']['name']} ({_pod_problem(p)})" for p in pods if not kube.pod_ready(p)]
    what = selector or f"namespace {namespace}"
    if len(ready) < min_ready:
        return FAIL, f"{len(ready)}/{len(pods)} pods ready for {what}; {'; '.join(bad)[:300] or 'no pods exist'}"
    if bad:
        return FAIL, f"not ready: {'; '.join(bad)[:300]}"
    return PASS, f"{len(ready)}/{len(pods)} pods ready for {what}"


def c_endpoints(service, namespace=kube.APP_NS, min_ready=1, **_):
    slices = kube.items("endpointslices", namespace=namespace, selector=f"kubernetes.io/service-name={service}")
    ready = sum(1 for s in slices for e in (s.get("endpoints") or [])
                if (e.get("conditions") or {}).get("ready") is not False)
    status = PASS if ready >= min_ready else FAIL
    return status, f"service {service} has {ready} ready endpoint(s)"


def c_reachable_from_nodes(service, port, namespace=kube.APP_NS, timeout_s=3, **_):
    """A TCP connection to the Service from a probe pod on every worker node (gym-system). It fails when some
    nodes cannot reach the Service (internalTrafficPolicy: Local, a node's network), whichever node the app's own
    pods happen to run on, so moving pods until the user journeys pass is not a fix."""
    host = f"{service}.{namespace}.svc.cluster.local"
    probes = toolbox.node_probes()
    missing = [n for n in kube.worker_nodes() if n not in probes]
    if missing:
        return UNKNOWN, f"no ready {toolbox.NODE_PROBE} pod on {', '.join(missing)} (run: python scripts/gym_setup.py)"
    blocked = []
    for node, pod in sorted(probes.items()):
        r = kube.exec_in(pod, ["sh", "-c", f"nc -z -w {timeout_s} {host} {port} && echo OPEN || echo BLOCKED"],
                         namespace=kube.GYM_NS, timeout=timeout_s + 30)
        out = r.stdout.strip()
        if out not in ("OPEN", "BLOCKED"):
            return UNKNOWN, f"probe on {node} failed: {(r.stderr or out).strip()[:200]}"
        if out == "BLOCKED":
            blocked.append(node)
    if blocked:
        return FAIL, (f"{host}:{port} unreachable from {', '.join(blocked)} "
                      f"({len(probes) - len(blocked)}/{len(probes)} worker nodes reach it)")
    return PASS, f"{host}:{port} reachable from all {len(probes)} worker nodes"


def c_no_new_restarts(selector, window_s=60, namespace=kube.APP_NS, **_):
    def total():
        return sum(kube.restarts(p) for p in kube.pods(selector, namespace=namespace))
    before = total()
    time.sleep(window_s)
    after = total()
    if after > before:
        return FAIL, f"{after - before} container restart(s) in {window_s}s for {selector}"
    return PASS, f"no restarts in {window_s}s for {selector}"


def _age_s(ts):
    import datetime
    t = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds()


def c_pods_stable(selector, min_age_s=90, namespace=kube.APP_NS, **_):
    """FAIL if pods keep being replaced or restarted: every pod must be older than min_age_s
    and no container may have restarted within the last min_age_s."""
    all_pods = kube.pods(selector, namespace=namespace)
    pods = _live(all_pods)
    evicted = [p for p in all_pods if p.get("status", {}).get("reason") == "Evicted"
               and _age_s(p["status"].get("startTime", "1970-01-01T00:00:00Z")) < min_age_s * 2]
    if not pods:
        return FAIL, f"no running pods for {selector}"
    problems = [f"{p['metadata']['name']} evicted" for p in evicted[:3]]
    for p in pods:
        name = p["metadata"]["name"]
        start = p.get("status", {}).get("startTime")
        if not start or _age_s(start) < min_age_s:
            problems.append(f"{name} is only {int(_age_s(start)) if start else 0}s old")
        for cs in p.get("status", {}).get("containerStatuses", []):
            t = (cs.get("lastState") or {}).get("terminated")
            if t and t.get("finishedAt") and _age_s(t["finishedAt"]) < min_age_s:
                problems.append(f"{name}/{cs['name']} restarted {int(_age_s(t['finishedAt']))}s ago ({t.get('reason')})")
    if problems:
        return FAIL, "; ".join(problems)[:300]
    return PASS, f"{len(pods)} pod(s) stable for >= {min_age_s}s ({selector})"


def c_nodes_ready(**_):
    bad = []
    for n in kube.items("nodes", namespace=None):
        ready = any(c["type"] == "Ready" and c["status"] == "True" for c in n["status"].get("conditions", []))
        if not ready:
            bad.append(f"{n['metadata']['name']} NotReady")
        if n["spec"].get("unschedulable"):
            bad.append(f"{n['metadata']['name']} cordoned")
        for t in n["spec"].get("taints", []) or []:
            if t.get("effect") in ("NoSchedule", "NoExecute") and "control-plane" not in t.get("key", ""):
                bad.append(f"{n['metadata']['name']} taint {t['key']}:{t['effect']}")
    return (FAIL, "; ".join(bad)) if bad else (PASS, "all nodes Ready and schedulable")


# ------------------------------------------------------------ user journeys
def _eval_journey(res, max_error_pct=0, max_avg_ms=2500, **_):
    n, ok = res["n"], res["ok"]
    err_pct = 100.0 * (n - ok) / n if n else 100.0
    avg = statistics.mean(res["ms"]) if res["ms"] else 0
    msg = f"{ok}/{n} ok, avg {avg:.0f}ms"
    if res["errors"]:
        msg += f"; e.g. {res['errors'][0][:150]}"
    if err_pct > max_error_pct:
        return FAIL, msg
    if avg > max_avg_ms:
        return FAIL, msg + f" (> {max_avg_ms}ms)"
    return PASS, msg


# ------------------------------------------------- load generator (Locust)
def _locust_stats():
    r = toolbox.http(kube.svc_url("load-generator", 8089, "/stats/requests"), timeout=10)
    if r["status"] != 200:
        raise kube.KubeError(f"load generator stats unavailable (HTTP {r['status']})")
    return {(s["method"], s["name"]): s for s in json.loads(r["body"])["stats"] if s["name"] != "Aggregated"}


def c_traffic(match, window_s=45, max_error_pct=5, max_avg_ms=None, min_requests=3, max_rps=None, **_):
    """Error rate / latency / request rate of real load-generator traffic whose name matches a regex."""
    pat = re.compile(match)
    a = _locust_stats()
    time.sleep(window_s)
    b = _locust_stats()
    n = f = t = 0
    for key, row in b.items():
        if not pat.search(key[1]):
            continue
        prev = a.get(key, {"num_requests": 0, "num_failures": 0, "avg_response_time": 0})
        dn = row["num_requests"] - prev["num_requests"]
        if dn < 0:  # load generator restarted; counters reset
            prev = {"num_requests": 0, "num_failures": 0, "avg_response_time": 0}
            dn = row["num_requests"]
        n += dn
        f += row["num_failures"] - prev["num_failures"]
        t += row["avg_response_time"] * row["num_requests"] - prev["avg_response_time"] * prev["num_requests"]
    rps = n / window_s
    if max_rps is not None and rps > max_rps:
        return FAIL, f"{rps:.1f} req/s for {match!r} over {window_s}s (max {max_rps})"
    if n < max(min_requests, 1):
        if max_rps is not None and n == 0:
            return PASS, f"0 req/s for {match!r} over {window_s}s"
        return UNKNOWN, f"only {n} requests matching {match!r} in {window_s}s"
    err = 100.0 * f / n
    avg = t / n
    msg = f"{f}/{n} failed ({err:.0f}%), avg {avg:.0f}ms, {rps:.1f} req/s over {window_s}s for {match!r}"
    if err > max_error_pct or (max_avg_ms and avg > max_avg_ms):
        return FAIL, msg
    return PASS, msg


# ------------------------------------------------------------- data plane
def c_kafka_lag(group, max_lag=50, **_):
    r = toolbox.kafka("kafka-consumer-groups.sh", "--describe", "--group", group)
    text = r.stdout + r.stderr
    if r.returncode != 0 or "does not exist" in text:
        return UNKNOWN, f"cannot read consumer group {group}: {text.strip()[:200]}"
    return kafka_lag_status(group, text, max_lag)


def kafka_lag_status(group, text, max_lag):
    """Lag of a consumer group from `kafka-consumer-groups.sh --describe` output. A partition with no
    committed offset (CURRENT-OFFSET and LAG are "-") has consumed nothing, so its lag is the whole
    log; counting it as 0 let a stuck consumer pass."""
    # Columns: GROUP TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG CONSUMER-ID HOST CLIENT-ID
    lag = 0
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6 or parts[0] != group:
            continue
        if parts[5].isdigit():
            lag += int(parts[5])
        elif parts[3] == "-" and parts[4].isdigit():
            lag += int(parts[4])
    if "has no active members" in text:
        return FAIL, f"consumer group {group} has no active members (lag {lag})"
    status = PASS if lag <= max_lag else FAIL
    return status, f"consumer group {group} lag {lag} (max {max_lag})"


def c_sql(query, expect_min=None, expect_max=None, database="astronomy_db", **_):
    r = kube.exec_in("deploy/astronomy-db", ["psql", "-U", "postgres", "-d", database, "-Atc", query])
    if r.returncode != 0:
        return UNKNOWN, f"query failed: {r.stderr.strip()[:200]}"
    try:
        value = float(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return UNKNOWN, f"non-numeric result {r.stdout.strip()[:80]!r}"
    if expect_min is not None and value < expect_min:
        return FAIL, f"{query} = {value:g} (< {expect_min})"
    if expect_max is not None and value > expect_max:
        return FAIL, f"{query} = {value:g} (> {expect_max})"
    return PASS, f"{query} = {value:g}"


def c_orders_recorded(timeout_s=90, **_):
    """Place a real order and require the accounting service to write it to the database."""
    def count():
        r = kube.exec_in("deploy/astronomy-db", ["psql", "-U", "postgres", "-d", "astronomy_db", "-Atc",
                                                 'select count(*) from accounting."order"'])
        return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
    before = count()
    if before is None:
        return UNKNOWN, "cannot read accounting.order"
    placed = toolbox.probe({"journeys": ["checkout"], "repeat": 1})["checkout"]
    if placed["ok"] < 1:
        return UNKNOWN, f"could not place a test order: {placed['errors'][:1]}"
    after = kube.wait_until(lambda: (c := count()) is not None and c > before and c, timeout=timeout_s, interval=5)
    if not after:
        return FAIL, f"order placed but accounting did not record it within {timeout_s}s (still {before} rows)"
    return PASS, f"accounting recorded the new order ({before} -> {after} rows)"


def c_http(url, method="GET", body=None, expect_status=200, max_ms=5000, contains=None, **_):
    r = toolbox.http(url, method=method, body=body, timeout=max(5, max_ms / 1000 + 2))
    msg = f"{method} {url} -> {r['status'] or 'no response'} in {r['ms']}ms"
    if r["status"] != expect_status:
        return FAIL, msg + f" (expected {expect_status}) {r['body'][:120]!r}"
    if contains and contains not in r["body"]:
        return FAIL, msg + f" (body lacks {contains!r})"
    if r["ms"] > max_ms:
        return FAIL, msg + f" (> {max_ms}ms)"
    return PASS, msg


def _jaeger_window(lookback):
    """Jaeger's HTTP API ignores `lookback` (only the UI uses it) and falls back to a much
    longer default window, so pass an explicit start/end in microseconds."""
    unit = {"s": 1, "m": 60, "h": 3600}[lookback[-1]]
    end = int(time.time() * 1e6)
    return f"start={end - int(float(lookback[:-1]) * unit * 1e6)}&end={end}"


def c_jaeger_traces(service, lookback="2m", min_traces=1, **_):
    url = kube.svc_url("jaeger", 16686, f"/jaeger/ui/api/traces?service={service}&{_jaeger_window(lookback)}"
                                        f"&limit={min_traces}")
    r = toolbox.http(url, timeout=15)
    if r["status"] != 200:
        return UNKNOWN, f"jaeger query failed: HTTP {r['status']} {r['body'][:120]!r}"
    try:
        n = len(json.loads(r["body"]).get("data") or [])
    except ValueError:
        return UNKNOWN, "jaeger returned a truncated/non-JSON body"
    status = PASS if n >= min_traces else FAIL
    return status, f"{n} trace(s) from {service} in the last {lookback}"


def c_jaeger_attr_absent(service, pattern, lookback="2m", limit=5, **_):
    """FAIL if recent traces of `service` contain text matching `pattern` (e.g. raw PII)."""
    url = kube.svc_url("jaeger", 16686, f"/jaeger/ui/api/traces?service={service}&{_jaeger_window(lookback)}"
                                        f"&limit={limit}")
    r = toolbox.http(url, timeout=20)
    if r["status"] != 200:
        return UNKNOWN, f"jaeger query failed: HTTP {r['status']}"
    try:
        traces = json.loads(r["body"]).get("data") or []
    except ValueError:
        return UNKNOWN, "jaeger returned a truncated/non-JSON body"
    if not traces:
        return UNKNOWN, f"no {service} traces in the last {lookback} to inspect"
    hits = re.findall(pattern, r["body"])
    if hits:
        return FAIL, f"{len(hits)} match(es) of {pattern!r} in {len(traces)} {service} trace(s), e.g. {hits[0]!r}"
    return PASS, f"no {pattern!r} in {len(traces)} {service} trace(s)"


def c_prometheus(query, min_value=None, max_value=None, **_):
    import urllib.parse
    url = kube.svc_url("prometheus", 9090, "/api/v1/query?query=" + urllib.parse.quote(query))
    r = toolbox.http(url, timeout=15)
    if r["status"] != 200:
        return UNKNOWN, f"prometheus query failed: HTTP {r['status']}"
    data = json.loads(r["body"]).get("data", {}).get("result", [])
    if not data:
        return FAIL, f"no data for {query}"
    value = float(data[0]["value"][1])
    if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
        return FAIL, f"{query} = {value:g}"
    return PASS, f"{query} = {value:g}"


def _node_summary(node):
    return json.loads(kube.kubectl("get", "--raw", f"/api/v1/nodes/{node}/proxy/stats/summary",
                                   namespace=None, timeout=60))


def c_cpu_usage(selector, max_cores=1.0, container=None, namespace=kube.APP_NS, **_):
    """CPU used by the selected pods' containers (kubelet stats), e.g. to catch a pegged container."""
    pods = [p for p in kube.pods(selector, namespace=namespace) if p.get("spec", {}).get("nodeName")]
    if not pods:
        return UNKNOWN, f"no scheduled pods for {selector}"
    worst = 0.0
    detail = []
    for node in sorted({p["spec"]["nodeName"] for p in pods}):
        names = {p["metadata"]["name"] for p in pods if p["spec"]["nodeName"] == node}
        for sp in _node_summary(node).get("pods", []):
            if sp["podRef"]["name"] not in names:
                continue
            for c in sp.get("containers", []):
                if container and c["name"] != container:
                    continue
                cores = (c.get("cpu", {}).get("usageNanoCores") or 0) / 1e9
                worst = max(worst, cores)
                detail.append(f"{sp['podRef']['name']}/{c['name']}={cores:.2f}")
    msg = f"cpu cores: {', '.join(detail) or 'no stats'} (max {max_cores})"
    return (FAIL if worst > max_cores else PASS), msg


def c_memory_usage(selector, max_mib=256, container=None, namespace=kube.APP_NS, **_):
    """Working-set memory of the selected pods' containers (kubelet stats). Catches leaks:
    leaked memory does not shrink until the process restarts."""
    pods = [p for p in kube.pods(selector, namespace=namespace) if p.get("spec", {}).get("nodeName")]
    if not pods:
        return UNKNOWN, f"no scheduled pods for {selector}"
    worst = 0.0
    detail = []
    for node in sorted({p["spec"]["nodeName"] for p in pods}):
        names = {p["metadata"]["name"] for p in pods if p["spec"]["nodeName"] == node}
        for sp in _node_summary(node).get("pods", []):
            if sp["podRef"]["name"] not in names:
                continue
            for c in sp.get("containers", []):
                if container and c["name"] != container:
                    continue
                mib = (c.get("memory", {}).get("workingSetBytes") or 0) / 2**20
                worst = max(worst, mib)
                detail.append(f"{c['name']}={mib:.0f}Mi")
    msg = f"memory: {', '.join(detail) or 'no stats'} (max {max_mib}Mi)"
    return (FAIL if worst > max_mib else PASS), msg


CHECKS = {
    "cpu_usage": c_cpu_usage, "orders_recorded": c_orders_recorded, "memory_usage": c_memory_usage,
    "pods_ready": c_pods_ready, "pods_stable": c_pods_stable, "endpoints": c_endpoints,
    "no_new_restarts": c_no_new_restarts, "reachable_from_nodes": c_reachable_from_nodes,
    "nodes_ready": c_nodes_ready, "traffic": c_traffic, "kafka_lag": c_kafka_lag, "sql": c_sql,
    "http": c_http, "jaeger_traces": c_jaeger_traces, "jaeger_attr_absent": c_jaeger_attr_absent,
    "prometheus": c_prometheus,
}


def describe(check):
    t = check["type"]
    key = check.get("journey") or check.get("selector") or check.get("service") or check.get("group") \
        or check.get("match") or check.get("url") or check.get("query") or ""
    return f"{t}:{key}" if key else t


def run_checks(checks):
    """Run a list of checks; returns [(check, status, message)]. Journeys are batched into one probe."""
    results = []
    journeys = [c for c in checks if c["type"] == "journey"]
    if journeys:
        plan = {"journeys": sorted({c["journey"] for c in journeys}),
                "repeat": max(int(c.get("repeat", 3)) for c in journeys),
                "timeout": max(float(c.get("timeout_s", 8)) for c in journeys)}
        try:
            probe = toolbox.probe(plan)
        except Exception as e:
            probe = None
            err = str(e)
        for c in journeys:
            if probe is None:
                results.append((c, UNKNOWN, f"probe unavailable: {err[:200]}"))
            else:
                results.append((c, *_eval_journey(probe[c["journey"]], **c)))
    for c in checks:
        if c["type"] == "journey":
            continue
        fn = CHECKS.get(c["type"])
        if fn is None:
            results.append((c, UNKNOWN, f"unknown check type {c['type']}"))
            continue
        try:
            results.append((c, *fn(**{k: v for k, v in c.items() if k != "type"})))
        except Exception as e:
            results.append((c, UNKNOWN, f"{type(e).__name__}: {str(e)[:200]}"))
    return results


def overall(results):
    return PASS if results and all(s == PASS for _, s, _ in results) else FAIL
