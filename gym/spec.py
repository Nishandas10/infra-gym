"""Loading scenario instances (scenarios/<id>/spec.yaml, generated from templates/; see gym/core)."""
from __future__ import annotations

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    """Accept a scenario folder or its spec.yaml; return (spec, scenario_dir).

    The spec is validated against the v2 instance schema and returned as a plain dict.
    """
    from .core.schema import Instance
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = (pathlib.Path.cwd() / p)
    if p.is_dir():
        p = p / "spec.yaml"
    spec = yaml.safe_load(p.read_text())
    if not isinstance(spec, dict) or spec.get("spec_version") != 2:
        raise ValueError(f"{p}: not a v2 scenario instance (regenerate with: python scripts/generate.py)")
    Instance.model_validate(spec)
    return spec, p.parent


def checks_of(spec):
    checks = (spec.get("verifier") or {}).get("checks")
    if not checks:
        raise ValueError(f"{spec.get('id')}: verifier.checks is empty")
    return checks


def prompt_of(spec, level="page"):
    """The task prompt at a hint level: page (symptoms only), ticket or hinted. Falls back to page."""
    prompts = spec["task"]["prompts"]
    return prompts.get(level) or prompts["page"]


def fault_label(spec):
    """Short label of what a scenario's fault does: its mechanism, or 'composite' for several steps."""
    steps = spec["fault"]["steps"]
    return steps[0]["mechanism"] if len(steps) == 1 else "composite"


def layer_of(spec):
    return spec["tags"]["layer"]


def tier_of(spec):
    return "hard" if spec["split"] == "hard" else "standard"


def all_specs():
    return sorted((REPO / "scenarios").glob("*/spec.yaml"))
