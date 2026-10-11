"""The static scenario checks (scripts/lint_scenarios.py) pass, and the prompt leak check works."""
import copy

import yaml

from gym.core import generate
from scripts.lint_scenarios import lint, prompt_leaks


def test_lint_clean():
    n_specs, _, problems = lint()
    assert n_specs > 0
    assert not problems, "\n".join(problems)


def _spec():
    built = generate.build_all()
    return yaml.safe_load(built["wl-listen-port-drift-014"]["spec.yaml"])


def test_leaky_page_prompt_is_caught():
    s = copy.deepcopy(_spec())
    s["task"]["prompts"]["page"] = "Orders fail since a NetworkPolicy change. Find the cause and fix it."
    assert prompt_leaks(s) == ["networkpolicy"]


def test_leak_terms_match_whole_words_only():
    s = copy.deepcopy(_spec())
    s["task"]["prompts"]["page"] = "Booms and zoom calls fail. Find the cause and fix it."   # contains 'oom'
    assert prompt_leaks(s) == []


def test_template_leak_terms_and_allow():
    s = copy.deepcopy(_spec())
    s["task"]["prompts"]["page"] = "The payment step fails after a DNS blip. Find the cause and fix it."
    assert prompt_leaks(s) == ["dns"]
    s["task"]["leak_allow"] = ["dns"]
    s["task"]["leak_terms"] = ["payment step"]
    assert prompt_leaks(s) == ["payment step"]
