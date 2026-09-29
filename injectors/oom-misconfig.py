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

    # Look up the target container's name instead of assuming it's index 0 --
    # this also lets the patch below merge by name instead of by position.
    container_name = run([
        "kubectl", "get", "deployment", f["target_deployment"],
        "-o", "jsonpath={.spec.template.spec.containers[0].name}",
    ]).strip()

    # A strategic merge patch (kubectl's default -- no --type flag needed)
    # creates missing fields instead of requiring them to already exist,
    # unlike a JSON patch "replace" op. This matters because some containers
    # only define resources.limits and have no resources.requests at all.
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": container_name,
                            "resources": {
                                "limits": {"memory": f["bad_memory_limit"]},
                                "requests": {"memory": f["bad_memory_request"]},
                            },
                        }
                    ]
                }
            }
        }
    }

    run([
        "kubectl", "patch", "deployment", f["target_deployment"],
        "-p", json.dumps(patch),
    ])

    # Force the currently-healthy pod out so the broken template takes over
    run(["kubectl", "delete", "pod", "-l", f["target_label"], "--wait=false"])
    print(f"\nInjected fault '{spec['id']}' into {f['target_deployment']}.")
    print("Give it 20-30 seconds, then run the verifier.")


if __name__ == "__main__":
    main()