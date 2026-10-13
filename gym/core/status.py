"""A scenario's validation status, computed from evidence only (results/validation.jsonl).

Only runs whose validation_hash equals the instance's count, so any change to what a live run
depends on (fault, checks, invariants, durability, reference fix, timings, files) starts the
evidence over. With the thresholds in templates/defaults.yaml (`status`):

  validated    at least min_runs runs, at most max_failures of them not VALIDATED
  quarantined  more than max_failures runs not VALIDATED (however many runs there are)
  draft        anything else: not enough runs yet

Not counted, because they say nothing about the scenario: runs that ended ENV_UNHEALTHY (the world
was already broken before the scenario started), INTERRUPTED (stopped by hand) or ENV_CHANGED (the
cluster context changed during the run), and runs listed in results/void.jsonl (one JSON object per
line: {"id", "started", "reason"}; append-only, so the evidence file itself is never edited).
"""
from __future__ import annotations

import collections
import dataclasses
import json
import pathlib
import statistics

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results" / "validation.jsonl"
NOT_COUNTED = {"ENV_UNHEALTHY", "INTERRUPTED", "ENV_CHANGED"}
STATUSES = ("validated", "quarantined", "draft")


@dataclasses.dataclass
class Status:
    status: str
    runs: int
    failures: int
    verdicts: dict            # verdict -> count, over the counted runs
    timings: dict             # median seconds over VALIDATED runs: detect_s, recover_s, ...

    @property
    def flake_rate(self):
        return self.failures / self.runs if self.runs else None

    def summary(self):
        if not self.runs:
            return "no runs"
        failed = ", ".join(f"{v} {n}" for v, n in sorted(self.verdicts.items()) if v != "VALIDATED")
        return f"{self.runs - self.failures}/{self.runs} validated" + (f" ({failed})" if failed else "")


def _jsonl(path):
    out = []
    if pathlib.Path(path).exists():
        for line in pathlib.Path(path).read_text().splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def load_records(path=RESULTS, void=None):
    """Every validation record, grouped by validation_hash (older records without one are skipped,
    and so are the runs listed in the void file next to `path`)."""
    by_hash = collections.defaultdict(list)
    void = pathlib.Path(path).with_name("void.jsonl") if void is None else void
    voided = {(v["id"], v["started"]) for v in _jsonl(void)}
    for rec in _jsonl(path):
        if (rec.get("id"), rec.get("started")) in voided:
            continue
        if rec.get("validation_hash"):
            by_hash[rec["validation_hash"]].append(rec)
    return by_hash


def compute(runs, rules):
    """Status of one instance from the records of its validation_hash. rules: {min_runs, max_failures}."""
    counted = [r for r in runs if r.get("verdict") not in NOT_COUNTED]
    verdicts = collections.Counter(r.get("verdict") or "UNKNOWN" for r in counted)
    failures = len(counted) - verdicts.get("VALIDATED", 0)
    if failures > rules["max_failures"]:
        status = "quarantined"
    elif len(counted) >= rules["min_runs"]:
        status = "validated"
    else:
        status = "draft"
    ok = [r for r in counted if r.get("verdict") == "VALIDATED"]
    timings = {}
    for key in sorted({k for r in ok for k in r.get("timings", {})}):
        vals = [r["timings"][key] for r in ok if key in r.get("timings", {})]
        timings[key] = round(statistics.median(vals))
    return Status(status, len(counted), failures, dict(verdicts), timings)


def of_spec(spec, records=None, rules=None):
    """Status of a loaded instance, from the current results file unless records are given."""
    if rules is None:
        from .generate import load_defaults
        rules = load_defaults().status.model_dump()
    records = load_records() if records is None else records
    return compute(records.get(spec["validation_hash"], []), rules)
