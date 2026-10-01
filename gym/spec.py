"""Loading scenario specs."""
from __future__ import annotations

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    """Accept a scenario folder or its spec.yaml; return (spec, scenario_dir)."""
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = (pathlib.Path.cwd() / p)
    if p.is_dir():
        p = p / "spec.yaml"
    spec = yaml.safe_load(p.read_text())
    return spec, p.parent


def checks_of(spec):
    checks = (spec.get("verifier") or {}).get("checks")
    if not checks:
        raise ValueError(f"{spec.get('id')}: verifier.checks is empty")
    return checks


def all_specs():
    return sorted((REPO / "scenarios").glob("*/spec.yaml"))
