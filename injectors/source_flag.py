"""Set a feature flag in its source of truth (the flagd-config ConfigMap) and restart flagd.

usage: python injectors/source_flag.py paymentFailure off
Unlike toggle_flag.py (which edits flagd's live file), this change survives flagd restarts.
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym import kube  # noqa: E402
from gym.faults import flags  # noqa: E402
from gym.undo import restart  # noqa: E402


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    flag, variant = sys.argv[1], sys.argv[2]
    flags.set_source_variant(flag, variant)
    time.sleep(20)  # let the kubelet see the new ConfigMap before the pod restarts
    restart("deployment/flagd")
    ok = kube.wait_until(lambda: flags.evaluate(flag).get("variant") == variant, timeout=180, interval=5)
    print(f"{flag} -> {variant}: {'loaded by flagd' if ok else 'NOT loaded yet: ' + str(flags.evaluate(flag))}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
