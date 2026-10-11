"""The static scenario checks (scripts/lint_scenarios.py) pass."""
from scripts.lint_scenarios import lint


def test_lint_clean():
    n_specs, _, problems = lint()
    assert n_specs > 0
    assert not problems, "\n".join(problems)
