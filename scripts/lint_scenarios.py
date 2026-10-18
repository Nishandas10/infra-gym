"""Static checks for every scenario template (no cluster needed).

usage: python scripts/lint_scenarios.py

Templates are validated against the v2 schema (gym/core/schema.py) by the generator; on top of
that this checks what the schema cannot see: known journeys, unique mechanisms, mechanisms that
were dropped, page prompts that give the cause away (templates/taxonomy.yaml prompt_leak_terms),
and that scenarios/ is up to date with templates/.

Warnings do not fail the lint: they point at scenarios worth strengthening (for example a
verifier with a single check, which a fix can pass by accident more easily than two specific ones).
"""
import ast
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from gym import checks  # noqa: E402
from gym.core import generate  # noqa: E402
from gym.core.schema import taxonomy  # noqa: E402

sys.path.insert(0, str(REPO / "bench"))
from safety import changing_commands  # noqa: E402


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


REPO_TOOLS = re.compile(r"(^|[\s;&|(])(python3?|helm)\s|(^|\s)(injectors|scripts|bench|verifiers)/")


GYM_NAMESPACES = re.compile(r"(-n|--namespace)[ =](gym-system|chaos-mesh)\b")


def uses_repo_tools(command):
    """True if a command needs this repo, a tool the agent's sandbox lacks (python, helm), or a namespace the agent
    cannot see (gym-system, chaos-mesh)."""
    return bool(REPO_TOOLS.search(command) or GYM_NAMESPACES.search(command))


def lint():
    """Return (number of scenarios, number of distinct mechanisms, problems, warnings)."""
    problems, warnings = [], []
    try:
        built = generate.build_all()      # schema validation, unique ids and mechanisms
    except Exception as e:
        return 0, 0, [f"{type(e).__name__}: {e}"], []
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
        # A diagnose scenario's fix is the operator's (the harness runs it); the agent never makes it.
        if s.get("bench_eligible", True) and s["task"].get("kind") != "diagnose" \
                and not s["reference"].get("agent_commands") \
                and any(uses_repo_tools(c) for c in s["reference"]["commands"]):
            problems.append(f"{sid}: reference.commands use the repo's scripts or the gym's namespaces, which the agent "
                            "cannot; add reference.agent_commands (kubectl, bash, sed)")
        if s["task"].get("kind") in ("false_alarm", "diagnose") \
                and changing_commands(s["reference"].get("agent_commands", [])):
            problems.append(f"{sid}: a {s['task']['kind'].replace('_', ' ')}'s reference.agent_commands may only look (the "
                            "oracle plays them as the agent, and any change fails the episode)")
        only = s["verifier"]["checks"]
        if len(only) == 1 and s.get("bench_eligible", True):
            warnings.append(f"{sid}: a single check ({checks.describe(only[0])}); add a second, more specific one "
                            "(pods_ready, endpoints, kafka_lag, orders_recorded...) if the fault has another outside signal")
    problems += [f"out of date: {p} (run: python scripts/generate.py)" for p in generate.stale(built)]
    return len(built), len(mechanisms), problems, warnings


def main():
    n_specs, n_mechanisms, problems, warnings = lint()
    print(f"{n_specs} scenarios, {n_mechanisms} distinct mechanisms, {len(problems)} problem(s), "
          f"{len(warnings)} warning(s)")
    for pr in problems:
        print("  -", pr)
    for w in warnings:
        print("  warning:", w)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
