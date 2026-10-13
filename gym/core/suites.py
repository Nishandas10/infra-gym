"""Suites: frozen, versioned lists of instances that models are compared on.

  suites/<name>.yaml            public suites (committed)
  private/suites/<name>.yaml    private suites, such as the held-out test suite. `private/` is a checkout
                                of a separate private repository and is git-ignored here; set
                                INFRA_GYM_PRIVATE to keep that checkout somewhere else.

A suite lists {id, hash} pairs; hash is the instance's content_hash when scripts/make_suite.py froze
the suite. verify() compares them with the current instances: a template change that alters how a
member behaves or is graded changes its content_hash, and the bench refuses to run the suite until a
new suite version is frozen. Benchmark rows record the suite's name, version and fingerprint and the
instance's hash, so every result traces back to exactly what ran.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib

import yaml

from . import status
from .schema import Suite

REPO = pathlib.Path(__file__).resolve().parents[2]
SUITES = REPO / "suites"


def private_root():
    return pathlib.Path(os.environ.get("INFRA_GYM_PRIVATE") or REPO / "private")


def suite_dirs():
    return [SUITES, private_root() / "suites"]


def find(ref):
    """A suite file from a path or a bare name (bench-v1-dev): suites/ first, then the private checkout."""
    p = pathlib.Path(ref)
    if p.suffix == ".txt":
        raise ValueError(f"{ref}: set files were replaced by suites (suites/<name>.yaml, made by scripts/make_suite.py)")
    if p.suffix in (".yaml", ".yml") or p.exists():
        if not p.exists():
            raise FileNotFoundError(f"no suite file {ref}")
        return p
    for d in suite_dirs():
        if (d / f"{ref}.yaml").exists():
            return d / f"{ref}.yaml"
    raise FileNotFoundError(f"no suite {ref!r} in {' or '.join(str(d) for d in suite_dirs())}")


def load(ref):
    path = find(ref)
    suite = Suite.model_validate(yaml.safe_load(path.read_text()))
    if path.stem != suite.name:
        raise ValueError(f"{path}: file name does not match suite name {suite.name!r}")
    if suite.visibility == "private" and path.resolve().is_relative_to(SUITES.resolve()):
        raise ValueError(f"{path}: a private suite must not live in the public repo; move it to "
                         f"{private_root() / 'suites'}")
    return suite


def all_suites():
    """Every suite file that can be found: public ones, then private ones (when the checkout is there)."""
    return [p for d in suite_dirs() if d.is_dir() for p in sorted(d.glob("*.yaml"))]


def fingerprint(suite):
    """Hash over what decides a suite's results: name, version, hint level and the {id, hash} list."""
    blob = json.dumps({"name": suite.name, "version": suite.version, "hint_level": suite.hint_level,
                       "instances": [[m.id, m.hash] for m in suite.instances]},
                      sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()


def instances():
    """Every current instance: {id: (spec, folder)}."""
    from gym.spec import all_specs, load as load_spec
    out = {}
    for p in all_specs():
        spec, folder = load_spec(p)
        out[spec["id"]] = (spec, folder)
    return out


@dataclasses.dataclass
class Problem:
    id: str
    kind: str      # missing | hash | not_eligible | quarantined | not_validated
    detail: str

    def __str__(self):
        return f"{self.id}: {self.detail}"


def verify(suite, insts=None, records=None):
    """Why the suite cannot run as frozen (empty list = it can). insts: instances(); records: status records."""
    insts = instances() if insts is None else insts
    records = status.load_records() if records is None else records
    out = []
    for m in suite.instances:
        if m.id not in insts:
            out.append(Problem(m.id, "missing", "no such scenario"))
            continue
        spec = insts[m.id][0]
        if spec["content_hash"] != m.hash:
            out.append(Problem(m.id, "hash", f"changed since the suite was frozen (suite has {m.hash[7:19]}, "
                                             f"the instance is now {spec['content_hash'][7:19]})"))
            continue
        if not spec.get("bench_eligible", True):
            out.append(Problem(m.id, "not_eligible", "not bench-eligible"))
            continue
        st = status.of_spec(spec, records)
        if st.status != "validated":
            kind = "quarantined" if st.status == "quarantined" else "not_validated"
            out.append(Problem(m.id, kind, f"{st.status} ({st.summary()})"))
    return out
