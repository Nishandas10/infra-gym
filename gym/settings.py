"""World settings: what the gym needs to know about the live cluster (worlds/<name>.yaml).

Scenarios describe faults; these settings describe where they run (namespaces, which nodes are
workers), so the same scenarios work on another cluster by changing the world file.
"""
from __future__ import annotations

import os
import pathlib

import yaml

WORLDS = pathlib.Path(__file__).resolve().parents[1] / "worlds"
DEFAULT_WORLD = "k8s-shop"


def load(name=DEFAULT_WORLD):
    data = yaml.safe_load((WORLDS / f"{name}.yaml").read_text())
    if os.environ.get("GYM_APP_NAMESPACE"):
        data["app_namespace"] = os.environ["GYM_APP_NAMESPACE"]
    return data


WORLD = load()
