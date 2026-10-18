"""Spec v2: the typed format of scenario templates (authored) and instances (generated).

A template lives in templates/<layer>/<id>/template.yaml, next to any files its fault reads
(chaos.yaml) and, for hand-written scenarios, its reference_solution.md. scripts/generate.py
resolves each template into an instance in scenarios/<id>/: defaults applied, hashes added.
Everything that runs a scenario (harness, bench, injectors, verifiers, judge) reads instances.

Tag values come from templates/taxonomy.yaml.
"""
from __future__ import annotations

import functools
import pathlib
import re
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}$")
MECHANISM_RE = re.compile(r"^[a-z0-9-]+/[a-z0-9-]+$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
# node/$workers: every worker node; node/$worker: one of them (the first by name)
COMPONENT_RE = re.compile(r"^[a-z]+/(?:[A-Za-z0-9._,-]+|\$workers?)$")
TAXONOMY_FILE = pathlib.Path(__file__).resolve().parents[2] / "templates" / "taxonomy.yaml"


@functools.cache
def taxonomy():
    return yaml.safe_load(TAXONOMY_FILE.read_text())


def _allowed(axis, value):
    allowed = taxonomy()[axis]
    if value not in allowed:
        raise ValueError(f"{axis} {value!r} is not in templates/taxonomy.yaml; allowed: {', '.join(allowed)}")
    return value


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Prompts(Strict):
    page: str = Field(min_length=10, description="Symptoms only, as an alert or a customer report reads")
    ticket: str | None = Field(None, description="The page plus what a first responder already found")
    hinted: str | None = Field(None, description="Points at the area of the cause; for calibration only")


class Task(Strict):
    kind: Literal["incident", "change", "diagnose", "false_alarm"] = "incident"
    prompts: Prompts
    leak_terms: list[str] = []    # extra terms the page prompt must not contain
    leak_allow: list[str] = []    # default leak terms this template's page prompt may contain


class Tags(Strict):
    layer: str
    symptom: str
    fix_type: list[str] = Field(min_length=1)
    drivers: list[str] = []
    injector: str

    @field_validator("layer", "symptom", "injector")
    @classmethod
    def known_value(cls, v, info):
        return _allowed(info.field_name, v)

    @field_validator("fix_type", "drivers")
    @classmethod
    def known_values(cls, v, info):
        for item in v:
            _allowed(info.field_name, item)
        if len(set(v)) != len(v):
            raise ValueError(f"{info.field_name} lists a value twice")
        return v


class RootCause(Strict):
    component: str = Field(description="kind/name of the faulty object, e.g. deployment/payment, flag/adFailure")
    namespace: str | None = Field("default", description="None for cluster-scoped objects")
    what: str = Field(min_length=10, description="One sentence: what is wrong with it")

    @field_validator("component")
    @classmethod
    def component_format(cls, v):
        if not COMPONENT_RE.match(v):
            raise ValueError(f"component {v!r} must look like 'kind/name' (lowercase kind)")
        return v


class GroundTruth(Strict):
    """What the incident really is: the answer key for grading a diagnosis."""
    root_causes: list[RootCause] = Field(min_length=1, description="One per fault that must be fixed")
    explanation: str = Field(min_length=20, description="How the fault causes the symptom")
    evidence: list[str] = Field(min_length=1, description="What a careful engineer can observe")
    red_herrings: list[str] = Field([], description="Loud or suspicious things that are not the cause")


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


class Restart(Strict):
    """A workload the fix must survive a restart of: its pods are deleted after recovery."""
    restart: str = Field(description="'deployment/x', 'daemonset/x', 'statefulset/x' or a pod label selector")
    namespace: str | None = Field(None, description="None = the world's app namespace")


def _forbidden_names(v):
    allowed = taxonomy()["forbidden_actions"]
    for name in v:
        if name not in allowed:
            raise ValueError(f"unknown forbidden action {name!r}; allowed: {', '.join(allowed)}")
    return v


def _invariant_names(v):
    from gym import checks
    for name in v:
        if name not in checks.INVARIANTS:
            raise ValueError(f"unknown invariant {name!r}; known: {', '.join(checks.INVARIANTS)}")
    return v


class Verifier(Strict):
    """The verifier as a template writes it; scripts/generate.py fills in what is left out."""
    checks: list[Check] = Field(min_length=1)
    alarm_checks: list[Check] | None = Field(None, min_length=1, description=(
        "false_alarm only: checks that FAIL once the alarm is raised, proving it is there (`checks` stay PASS)"))
    invariants: list[str] | None = None      # None = templates/defaults.yaml
    durability: list[Restart] | None = None  # None = derived from the fault (gym/core/generate.py)
    forbidden_extra: list[str] = []          # added to the defaults.yaml forbidden list

    @field_validator("invariants")
    @classmethod
    def known_invariants(cls, v):
        return v if v is None else _invariant_names(v)

    @field_validator("forbidden_extra")
    @classmethod
    def known_forbidden(cls, v):
        return _forbidden_names(v)


class ResolvedVerifier(Strict):
    """The verifier of an instance: everything explicit."""
    checks: list[Check] = Field(min_length=1)
    alarm_checks: list[Check] | None = Field(None, min_length=1)   # false_alarm only; absent otherwise
    invariants: list[str]
    durability: list[Restart]
    forbidden: list[str]

    @field_validator("invariants")
    @classmethod
    def known_invariants(cls, v):
        return _invariant_names(v)

    @field_validator("forbidden")
    @classmethod
    def known_forbidden(cls, v):
        return _forbidden_names(v)


class Reference(Strict):
    commands: list[str] = Field(description="The reference fix, run by the validation harness; empty only for a "
                                "false alarm (nothing to fix)")
    agent_commands: list[str] = Field([], description="The same fix as the agent can run it in its sandbox (kubectl, "
                                      "bash, sed), when `commands` uses the repo's scripts; run by the oracle episodes "
                                      "(bench/agent_bench.py oracle). In no hash: it changes neither the fault nor the grading")
    fix: str | None = Field(None, description="The fix in words, with any accepted alternatives (answer key)")
    traps: list[str] = []                # why the scenario is hard (Hard tier)


class Validation(Strict):
    """Overrides of the defaults.yaml timings (seconds)."""
    baseline_timeout_s: int | None = Field(None, gt=0)
    detect_timeout_s: int | None = Field(None, gt=0)
    hold_s: int | None = Field(None, gt=0)
    recover_timeout_s: int | None = Field(None, gt=0)
    poll_s: int | None = Field(None, gt=0)
    restart_settle_s: int | None = Field(None, ge=0)


class ResolvedValidation(Strict):
    baseline_timeout_s: int = Field(gt=0)
    detect_timeout_s: int = Field(gt=0)
    hold_s: int = Field(gt=0)
    recover_timeout_s: int = Field(gt=0)
    poll_s: int = Field(gt=0)
    restart_settle_s: int = Field(ge=0)


class Budget(Strict):
    max_steps: int = Field(gt=0)
    wall_s: int = Field(gt=0)


class Template(Strict):
    spec_version: Literal[2]
    id: str
    version: int = Field(1, ge=1, description="Bump on any change that affects behaviour")
    title: str
    mechanism: str = Field(description="Root-cause class; must be unique across templates")
    split: Literal["train", "hard"] = Field(description="Tier: standard scenarios (train) or the Hard tier")
    seed: int
    world: Literal["k8s-shop"] = "k8s-shop"
    bench_eligible: bool = True
    tools: list[str] | None = None        # None = templates/defaults.yaml
    task: Task
    tags: Tags
    params: dict[str, Any] = {}           # Phase 8 (training): parameter space; empty = one instance
    fault: Fault
    verifier: Verifier
    ground_truth: GroundTruth
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

    @model_validator(mode="after")
    def task_kind_rules(self):
        """A false alarm raises an alarm (alarm_checks) and has nothing to fix; every other kind has a fix."""
        if self.task.kind == "false_alarm":
            if not self.verifier.alarm_checks:
                raise ValueError("a false_alarm needs verifier.alarm_checks (checks that FAIL while the alarm is up)")
            if self.reference.commands:
                raise ValueError("a false_alarm has nothing to fix: reference.commands must be []")
        else:
            if self.verifier.alarm_checks:
                raise ValueError("verifier.alarm_checks is only for task.kind false_alarm")
            if not self.reference.commands:
                raise ValueError("reference.commands is empty; only a false_alarm has nothing to fix")
        return self


class InstanceOf(Strict):
    template: str
    version: int
    params: dict[str, Any] = {}


class Instance(Template):
    """A generated, fully resolved scenario (scenarios/<id>/spec.yaml)."""
    instance_of: InstanceOf
    content_hash: str      # everything that decides behaviour and grading (results, suites)
    validation_hash: str   # only what a live validation run depends on (validation status)
    status: Literal["validated", "quarantined", "draft"]   # from evidence (gym/core/status.py); in no hash
    tools: list[str]
    budget: Budget
    verifier: ResolvedVerifier
    validation: ResolvedValidation

    @field_validator("content_hash", "validation_hash")
    @classmethod
    def hash_format(cls, v):
        if not HASH_RE.match(v):
            raise ValueError("hashes must be 'sha256:<64 hex>'")
        return v


SUITE_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SuiteMember(Strict):
    id: str
    hash: str = Field(description="The instance's content_hash when the suite was frozen")

    @field_validator("hash")
    @classmethod
    def hash_format(cls, v):
        if not HASH_RE.match(v):
            raise ValueError("hashes must be 'sha256:<64 hex>'")
        return v


class Suite(Strict):
    """A frozen, versioned list of instances that models are compared on (gym/core/suites.py)."""
    name: str
    version: int = Field(ge=1, description="Bump on any change to the instance list or a member's hash")
    visibility: Literal["public", "private"]
    hint_level: Literal["page", "ticket", "hinted"] = "page"
    description: str = ""
    selection: dict[str, Any] = {}        # how scripts/make_suite.py chose the instances; informational
    instances: list[SuiteMember] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def name_format(cls, v):
        if not SUITE_NAME_RE.match(v):
            raise ValueError(f"suite name {v!r} must be lowercase words joined by '-'")
        return v

    @field_validator("instances")
    @classmethod
    def unique_ids(cls, v):
        ids = [m.id for m in v]
        dups = sorted({i for i in ids if ids.count(i) > 1})
        if dups:
            raise ValueError(f"listed more than once: {', '.join(dups)}")
        return v


class StatusRules(Strict):
    min_runs: int = Field(gt=0)
    max_failures: int = Field(ge=0)


class Defaults(Strict):
    forbidden: list[str]
    invariants: list[str]
    validation: ResolvedValidation
    status: StatusRules
    tools: list[str]
    budget: Budget

    @field_validator("invariants")
    @classmethod
    def known_invariants(cls, v):
        return _invariant_names(v)

    @field_validator("forbidden")
    @classmethod
    def known_forbidden(cls, v):
        return _forbidden_names(v)
