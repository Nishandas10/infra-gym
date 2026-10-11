"""Static checks for every scenario template (no cluster needed).

usage: python scripts/lint_scenarios.py

Templates are validated against the v2 schema (gym/core/schema.py) by the generator; on top of
that this checks what the schema cannot see: known journeys, unique mechanisms, mechanisms that
were dropped, and that scenarios/ is up to date with templates/.
"""
import ast
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from gym.core import generate  # noqa: E402


def journeys():
    tree = ast.parse((REPO / "gym" / "probe_script.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "JOURNEYS":
            return {k.value for k in node.value.keys}
    return set()


def lint():
    """Return (number of scenarios, number of distinct mechanisms, list of problems)."""
    problems = []
    try:
        built = generate.build_all()      # schema validation, unique ids and mechanisms
    except Exception as e:
        return 0, 0, [f"{type(e).__name__}: {e}"]
    known_journeys = journeys()
    dropped = yaml.safe_load((REPO / "templates" / "dropped.yaml").read_text()) or {}
    mechanisms = set()
    for sid, files in built.items():
        s = yaml.safe_load(files["spec.yaml"])
        mechanisms.add(s["mechanism"])
        if s["mechanism"] in dropped:
            problems.append(f"{sid}: mechanism {s['mechanism']} was dropped ({dropped[s['mechanism']][:80]}...)")
        for c in s["verifier"]["checks"]:
            if c["type"] == "journey" and c.get("journey") not in known_journeys:
                problems.append(f"{sid}: unknown journey {c.get('journey')}")
    problems += [f"out of date: {p} (run: python scripts/generate.py)" for p in generate.stale(built)]
    return len(built), len(mechanisms), problems


def main():
    n_specs, n_mechanisms, problems = lint()
    print(f"{n_specs} scenarios, {n_mechanisms} distinct mechanisms, {len(problems)} problem(s)")
    for pr in problems:
        print("  -", pr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
