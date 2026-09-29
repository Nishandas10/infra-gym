"""Verifier for the 'memory_limit_misconfig' family.

Checks REAL, OUTSIDE evidence only: pod health via the Kubernetes API,
and live traffic success rate via the load generator's own stats feed.
Never trusts anything the agent says.
"""

import argparse
import json
import subprocess
import sys
from typing import Tuple, Optional

import requests
import yaml

# Configuration constants
LOADGEN_STATS_URL = "http://localhost:8080/loadgen/stats/requests"
LOADGEN_TIMEOUT_SEC = 5
ERROR_RATE_THRESHOLD_PCT = 5.0
TRAFFIC_MATCH_SUBSTRING = "cart"


def pods_ready(label: str) -> Tuple[bool, str]:
    """Check if all pods matching the label are Ready.

    Args:
        label: Kubernetes label selector (e.g., "app=cart")

    Returns:
        (is_ready, message) where is_ready is bool and message explains why
    """
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-l", label, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        pods = json.loads(result.stdout)["items"]
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        return False, f"kubectl query failed: {e}"

    if not pods:
        return False, "no pods found"

    for pod in pods:
        statuses = pod["status"].get("containerStatuses", [])
        if not all(s.get("ready") for s in statuses):
            return False, f"pod {pod['metadata']['name']} not ready"

    return True, "all target pods ready"


def checkout_error_rate(
    match_substring: str = TRAFFIC_MATCH_SUBSTRING,
) -> Tuple[Optional[float], str]:
    """Check the real traffic error rate from the load generator.

    Args:
        match_substring: Only count requests whose name contains this

    Returns:
        (error_rate_pct, message) where error_rate_pct is None if unknown
    """
    try:
        resp = requests.get(LOADGEN_STATS_URL, timeout=LOADGEN_TIMEOUT_SEC)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return None, f"could not reach load generator: {e}"
    except json.JSONDecodeError as e:
        return None, f"load generator returned invalid JSON: {e}"

    total_req = 0
    total_fail = 0

    for row in data.get("stats", []):
        if match_substring.lower() in row.get("name", "").lower():
            total_req += row.get("num_requests", 0)
            total_fail += row.get("num_failures", 0)

    if total_req == 0:
        return None, "no matching requests yet -- wait 20s and retry"

    error_pct = (total_fail / total_req) * 100
    return error_pct, f"{total_fail}/{total_req} requests failed"


def main() -> None:
    """Run the verifier and report results."""
    parser = argparse.ArgumentParser(
        description="Verify system health for memory_limit_misconfig scenario"
    )
    parser.add_argument("spec_path", help="Path to scenario spec.yaml")
    args = parser.parse_args()

    try:
        with open(args.spec_path) as f:
            spec = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: spec file not found: {args.spec_path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: invalid YAML in {args.spec_path}: {e}", file=sys.stderr)
        sys.exit(1)

    label = spec["fault"]["target_label"]

    # Check pod health
    ok_pods, pod_msg = pods_ready(label)
    print(f"[pods]   {'PASS' if ok_pods else 'FAIL'} - {pod_msg}")

    # Check traffic error rate
    error_rate, rate_msg = checkout_error_rate()
    if error_rate is None:
        print(f"[traffic] UNKNOWN - {rate_msg}")
        ok_rate = False
    else:
        ok_rate = error_rate < ERROR_RATE_THRESHOLD_PCT
        print(f"[traffic] {'PASS' if ok_rate else 'FAIL'} - "
              f"error rate {error_rate:.1f}% ({rate_msg})")

    # Overall verdict
    overall = ok_pods and (error_rate is not None and error_rate < ERROR_RATE_THRESHOLD_PCT)
    print(f"\nOVERALL: {'PASS - system healthy' if overall else 'FAIL - system unhealthy'}")

    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
