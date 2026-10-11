"""Static checks for every scenario spec (no cluster needed).

usage: python scripts/lint_scenarios.py
"""
import ast
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from gym import checks, faults  # noqa: E402


def journeys():
    tree = ast.parse((REPO / "gym" / "probe_script.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "JOURNEYS":
            return {k.value for k in node.value.keys}
    return set()


def fault_types(fault):
    yield fault["type"]
    for step in fault.get("steps", []):
        yield from fault_types(step)


def lint():
    """Return (number of specs, number of distinct mechanisms, list of problems)."""
    known_journeys = journeys()
    problems = []
    mechanisms = {}
    specs = sorted((REPO / "scenarios").glob("*/spec.yaml"))
    for p in specs:
        s = yaml.safe_load(p.read_text())
        sid = s.get("id")
        if sid != p.parent.name:
            problems.append(f"{p.parent.name}: id {sid!r} does not match folder")
        for t in fault_types(s["fault"]):
            if t not in faults.REGISTRY:
                problems.append(f"{sid}: unknown fault type {t}")
        for c in (s.get("verifier") or {}).get("checks") or []:
            if c["type"] == "journey":
                if c["journey"] not in known_journeys:
                    problems.append(f"{sid}: unknown journey {c['journey']}")
            elif c["type"] not in checks.CHECKS:
                problems.append(f"{sid}: unknown check type {c['type']}")
        if not (s.get("verifier") or {}).get("checks"):
            problems.append(f"{sid}: no verifier checks")
        if not (s.get("solution") or {}).get("commands"):
            problems.append(f"{sid}: no solution commands")
        if not (p.parent / "reference_solution.md").exists():
            problems.append(f"{sid}: missing reference_solution.md")
        m = (s.get("meta") or {}).get("mechanism")
        if not m:
            problems.append(f"{sid}: no meta.mechanism")
        mechanisms.setdefault(m, []).append(sid)
    for m, ids in mechanisms.items():
        if len(ids) > 1:
            problems.append(f"mechanism {m} used by {ids} (not unique)")
    return len(specs), len(mechanisms), problems


def main():
    n_specs, n_mechanisms, problems = lint()
    print(f"{n_specs} specs, {n_mechanisms} distinct mechanisms, {len(problems)} problem(s)")
    for pr in problems:
        print("  -", pr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
