"""Run one complete episode: reset -> inject -> confirm broken.

Leaves the world broken and waiting for someone (you, or an agent) to fix it.
After a fix, run the verifier again, then reset_world.sh when done.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Configuration constants
SLEEP_AFTER_INJECT_SEC = 30
RESET_SCRIPT = "./scripts/reset_world.sh"
# Generic injector and verifier: they read fault.type and verifier.checks from
# the spec, so any scenario works (not just k8s-oom-cascade-001).
VERIFIER_SCRIPT = "verifiers/verify.py"
INJECTOR_SCRIPT = "injectors/inject.py"


def run_command(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result.

    Args:
        cmd: Command as a list (e.g., ["python", "script.py", "arg"])
        check: If True, raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess with returncode, stdout, stderr

    Raises:
        subprocess.CalledProcessError: If check=True and returncode != 0
    """
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def reset_world() -> None:
    """Reset the cluster to a known-good state via Helm."""
    print("\n1/4 Resetting world...")
    try:
        run_command(["bash", RESET_SCRIPT], check=True)
        print("✓ World reset successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Reset failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)


def verify_baseline(spec_path: str) -> None:
    """Verify the cluster is healthy before injecting faults.

    Args:
        spec_path: Path to the scenario spec.yaml

    Raises:
        SystemExit: If baseline is not healthy
    """
    print("\n2/4 Confirming healthy baseline...")
    result = run_command(["python", VERIFIER_SCRIPT, spec_path], check=False)

    if result.returncode != 0:
        print(f"\n✗ Baseline was not healthy", file=sys.stderr)
        print("Fix your environment before injecting faults.", file=sys.stderr)
        sys.exit(1)

    print("✓ Baseline is healthy")


def inject_fault(spec_path: str) -> None:
    """Inject the configured fault into the cluster.

    Args:
        spec_path: Path to the scenario spec.yaml

    Raises:
        subprocess.CalledProcessError: If injection fails
    """
    print("\n3/4 Injecting fault...")
    try:
        run_command(["python", INJECTOR_SCRIPT, spec_path], check=True)
        print("✓ Fault injected successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Injection failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)


def verify_broken(spec_path: str) -> None:
    """Verify the cluster is now broken as expected.

    Args:
        spec_path: Path to the scenario spec.yaml
    """
    print(f"\n4/4 Waiting {SLEEP_AFTER_INJECT_SEC}s for fault to take effect...")
    time.sleep(SLEEP_AFTER_INJECT_SEC)

    print("\nConfirming fault injection succeeded...")
    run_command(["python", VERIFIER_SCRIPT, spec_path], check=False)


def main() -> None:
    """Parse args and run the full episode."""
    parser = argparse.ArgumentParser(
        description="Run a complete fault-injection episode: reset -> inject -> verify",
        epilog="After the fault is injected, the cluster will be broken. Run the verifier "
               "after fixing it, then run reset_world.sh to clean up.",
    )
    parser.add_argument(
        "spec_path",
        nargs="?",
        default="scenarios/k8s-oom-cascade-001/spec.yaml",
        help="Path to scenario spec.yaml (default: k8s-oom-cascade-001)",
    )
    args = parser.parse_args()

    # Validate spec file exists
    spec_file = Path(args.spec_path)
    if not spec_file.exists():
        print(f"ERROR: spec file not found: {args.spec_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Running episode for: {args.spec_path}")

    # Run the episode
    reset_world()
    verify_baseline(args.spec_path)
    inject_fault(args.spec_path)
    verify_broken(args.spec_path)

    # Final message
    print(
        "\n" + "="*70
        + "\nWorld is now broken and waiting."
        + "\nGo fix it, then re-run the verifier:"
        + f"\n  python {VERIFIER_SCRIPT} {args.spec_path}"
        + "\nThen undo the injection exactly (a Helm reset alone does not remove"
        + "\nthings like NetworkPolicies, node taints or datastore settings):"
        + f"\n  python {INJECTOR_SCRIPT} {args.spec_path} --revert"
        + "\n" + "="*70
    )


if __name__ == "__main__":
    main()
