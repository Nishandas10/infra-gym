"""Spec v2: the typed format of scenario templates (authored) and instances (generated).

A template lives in templates/<family>/<id>/template.yaml, next to any files its fault reads
(chaos.yaml) and, for hand-written scenarios, its reference_solution.md. scripts/generate.py
resolves each template into an instance in scenarios/<id>/: defaults applied, a content hash
added. Everything that runs a scenario (harness, bench, injectors, verifiers) reads instances.

Fields marked "Phase 2" are optional until the taxonomy and ground truth are filled in.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}$")
MECHANISM_RE = re.compile(r"^[a-z0-9-]+/[a-z0-9-]+$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Prompts(Strict):
    page: str = Field(min_length=10, description="Symptoms only, as a page or customer ticket reads")
    ticket: str | None = None
    hinted: str | None = None


class Task(Strict):
    kind: Literal["incident", "change", "diagnose", "false_alarm"] = "incident"
    prompts: Prompts


class Tags(Strict):
    """Phase 2: the taxonomy axes. Values are free text until templates/taxonomy.yaml exists."""
    layer: str | None = None
    symptom: str | None = None
    fix_type: str | None = None
    drivers: list[str] = []
    injector: str | None = None


class Step(BaseModel):
    """One fault step. Besides `mechanism`, its keys are that mechanism's own parameters."""
    model_config = ConfigDict(extra="allow")
    mechanism: str

    @field_validator("mechanism")
    @classmethod
    def known_mechanism(cls, v):
        from gym import faults
        if v not in faults.REGISTRY:
            raise ValueError(f"unknown mechanism {v!r}; known: {', '.join(sorted(faults.REGISTRY))}")
        return v


class Fault(Strict):
    steps: list[Step] = Field(min_length=1)
    restart_on_revert: list[str] | None = None
    revert_hooks: list[dict[str, Any]] | None = None


class Check(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str

    @field_validator("type")
    @classmethod
    def known_check(cls, v):
        from gym import checks
        if v != "journey" and v not in checks.CHECKS:
            raise ValueError(f"unknown check type {v!r}")
        return v


class Verifier(Strict):
    checks: list[Check] = Field(min_length=1)
    root_cause: list[str] = []
    forbidden: list[str] | None = None   # None in a template = templates/defaults.yaml


class Reference(Strict):
    commands: list[str] = Field(min_length=1, description="The reference fix, run by the validation harness")
    cause: str | None = None
    diagnose: list[str] = []
    traps: list[str] = []
    noise: list[str] = []


class Validation(Strict):
    baseline_timeout_s: int | None = None
    detect_timeout_s: int | None = None
    recover_timeout_s: int | None = None
    hold_s: int | None = None
    poll_s: int | None = None
    restart_after_fix: list[str] | None = None
    restart_settle_s: int | None = None


class Budget(Strict):
    max_steps: int = Field(gt=0)
    wall_s: int = Field(gt=0)


class Template(Strict):
    spec_version: Literal[2]
    id: str
    version: int = Field(1, ge=1, description="Bump on any change that affects behaviour")
    title: str
    mechanism: str = Field(description="Root-cause class; must be unique across templates")
    family: str = Field(description="Legacy grouping; replaced by tags in Phase 2")
    split: Literal["train", "hard"]
    seed: int
    world: Literal["k8s-shop"] = "k8s-shop"
    bench_eligible: bool = True
    tools: list[str] | None = None        # None = templates/defaults.yaml
    task: Task
    tags: Tags = Tags()
    params: dict[str, Any] = {}           # Phase 8 (training): parameter space; empty = one instance
    fault: Fault
    verifier: Verifier
    reference: Reference
    validation: Validation = Validation()
    budget: Budget | None = None          # None = templates/defaults.yaml
    notes: list[str] = []                 # authoring notes: measurements, why a value was chosen
    meta: dict[str, Any] = {}             # informational only; never read by the engine

    @field_validator("id")
    @classmethod
    def id_format(cls, v):
        if not ID_RE.match(v):
            raise ValueError(f"id {v!r} must be lowercase words joined by '-' and end in a 3-digit number")
        return v

    @field_validator("mechanism")
    @classmethod
    def mechanism_format(cls, v):
        if not MECHANISM_RE.match(v):
            raise ValueError(f"mechanism {v!r} must look like 'family/name'")
        return v


class InstanceOf(Strict):
    template: str
    version: int
    params: dict[str, Any] = {}


class Instance(Template):
    """A generated, fully resolved scenario (scenarios/<id>/spec.yaml)."""
    instance_of: InstanceOf
    content_hash: str
    tools: list[str]
    budget: Budget
    verifier: Verifier

    @field_validator("content_hash")
    @classmethod
    def hash_format(cls, v):
        if not HASH_RE.match(v):
            raise ValueError("content_hash must be 'sha256:<64 hex>'")
        return v

    @model_validator(mode="after")
    def resolved(self):
        if self.verifier.forbidden is None:
            raise ValueError("an instance must list verifier.forbidden (defaults are resolved by the generator)")
        return self


class Defaults(Strict):
    forbidden: list[str]
    tools: list[str]
    budget: Budget
