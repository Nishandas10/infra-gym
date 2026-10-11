"""Static checks for every scenario template (no cluster needed).

usage: python scripts/lint_scenarios.py

Templates are validated against the v2 schema (gym/core/schema.py) by the generator; on top of
that this checks what the schema cannot see: known journeys, unique mechanisms, mechanisms that
were dropped, page prompts that give the cause away (templates/taxonomy.yaml prompt_leak_terms),
and that scenarios/ is up to date with templates/.
"""
import ast
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from gym.core import generate  # noqa: E402
from gym.core.schema import taxonomy  # noqa: E402


def journeys():
    tree = ast.parse((REPO / "gym" / "probe_script.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "JOURNEYS":
            return {k.value for k in node.value.keys}
    return set()


def prompt_leaks(spec):
    """Leak terms found in the page prompt (case-insensitive, whole words or phrases)."""
    task = spec["task"]
    terms = set(taxonomy()["prompt_leak_terms"]) | set(task.get("leak_terms", []))
    terms -= set(task.get("leak_allow", []))
    page = task["prompts"]["page"].lower()
    return sorted(t for t in terms if re.search(rf"(?<![a-z0-9]){re.escape(t.lower())}(?![a-z0-9])", page))


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
        leaks = prompt_leaks(s)
        if leaks:
            problems.append(f"{sid}: the page prompt gives the cause away ({', '.join(leaks)}); move that detail "
                            "to prompts.ticket, or add the term to task.leak_allow if it is a user-visible symptom")
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
