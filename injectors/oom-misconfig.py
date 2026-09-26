"""Injector for the 'memory_limit_misconfig' fault family.

Patches a Deployment's memory request/limit to an unworkably small value,
then kills the currently-running (healthy) pod so Kubernetes is forced to
replace it with a new, broken one.
"""

import argparse
import json
import subprocess
import sys
import yaml

def run(cmd):
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("spec_path")
    args = p.parse_args()
    spec = yaml.safe_load(open(args.spec_path))
    f = spec["fault"]

    patch = [
        {
            "op": "replace",
            "path": "/spec/template/spec/containers/0/resources/limits/memory",
            "value": f["bad_memory_limit"],
        },
        {
            "op": "replace",
            "path": "/spec/template/spec/containers/0/resources/requests/memory",
            "value": f["bad_memory_request"],
        },
    ]

    run([
        "kubectl", "patch", "deployment", f["target_deployment"],
        "--type=json", "-p", json.dumps(patch),
    ])

    # Force the currently-healthy pod out so the broken template takes over
    run(["kubectl", "delete", "pod", "-l", f["target_label"], "--wait=false"])
    print(f"\nInjected fault '{spec['id']}' into {f['target_deployment']}.")
    print("Give it 20-30 seconds, then run the verifier.")


if __name__ == "__main__":
    main()