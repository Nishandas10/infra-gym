"""Validation status from evidence (gym/core/status.py) and how the generator records it."""
from __future__ import annotations

import json

import pytest
import yaml

from gym.core import generate, status

RULES = {"min_runs": 5, "max_failures": 1}
SID = "wl-listen-port-drift-014"


def runs(*verdicts, vhash="sha256:x"):
    return [{"id": SID, "validation_hash": vhash, "verdict": v, "timings": {"detect_s": 10 + i}}
            for i, v in enumerate(verdicts)]


@pytest.mark.parametrize("verdicts, want", [
    ((), "draft"),
    (("VALIDATED",) * 4, "draft"),
    (("VALIDATED",) * 5, "validated"),
    (("VALIDATED",) * 4 + ("SELF_HEALED",), "validated"),            # one failure allowed
    (("VALIDATED",) * 3 + ("SELF_HEALED", "NOT_DETECTED"), "quarantined"),
    (("ERROR", "FIX_NOT_DURABLE"), "quarantined"),                     # quarantined before 5 runs
    (("VALIDATED",) * 4 + ("ENV_UNHEALTHY",), "draft"),                 # a broken world says nothing
    (("VALIDATED",) * 5 + ("ENV_UNHEALTHY",) * 3, "validated"),
    (("VALIDATED",) * 4 + ("INTERRUPTED",), "draft"),                   # stopped by hand: not evidence
])
def test_rules(verdicts, want):
    assert status.compute(runs(*verdicts), RULES).status == want


def test_summary_and_timings():
    st = status.compute(runs("VALIDATED", "SELF_HEALED", "VALIDATED"), RULES)
    assert (st.runs, st.failures, st.summary()) == (3, 1, "2/3 validated (SELF_HEALED 1)")
    assert st.timings == {"detect_s": 11}          # median over the VALIDATED runs only (10, 12)


def test_only_runs_of_the_current_version_count(tmp_path):
    path = tmp_path / "validation.jsonl"
    old = runs(*("VALIDATED",) * 5, vhash="sha256:old")
    legacy = [{"id": SID, "verdict": "VALIDATED"}] * 5               # older records without a hash
    path.write_text("".join(json.dumps(r) + "\n" for r in old + legacy) + "not json\n")
    records = status.load_records(path)
    assert set(records) == {"sha256:old"}
    assert status.of_spec({"validation_hash": "sha256:new"}, records, RULES).status == "draft"
    assert status.of_spec({"validation_hash": "sha256:old"}, records, RULES).status == "validated"


def test_generator_writes_status_outside_both_hashes():
    draft = generate.build_all(records={})
    spec = yaml.safe_load(draft[SID]["spec.yaml"])
    assert spec["status"] == "draft"
    done = generate.build_all(records={spec["validation_hash"]: runs(*("VALIDATED",) * 5)})
    after = yaml.safe_load(done[SID]["spec.yaml"])
    assert after["status"] == "validated"
    assert (after["content_hash"], after["validation_hash"]) == (spec["content_hash"], spec["validation_hash"])
    other = yaml.safe_load(done["node-taint-046"]["spec.yaml"])
    assert other["status"] == "draft"                                 # evidence is per validation_hash


def test_catalog_reports_status():
    built = generate.build_all(records={})
    vhash = yaml.safe_load(built[SID]["spec.yaml"])["validation_hash"]
    records = {vhash: runs("VALIDATED", "ERROR", "FIX_NOT_DURABLE")}
    text = generate.catalog_markdown(built, records)
    assert "0 validated, 1 quarantined, 94 draft" in text
    row = next(line for line in text.splitlines() if line.startswith(f"| `{SID}`"))
    assert "| quarantined | 1/3 validated (ERROR 1, FIX_NOT_DURABLE 1) |" in row


def test_voided_runs_do_not_count(tmp_path):
    path = tmp_path / "validation.jsonl"
    recs = [dict(r, started=f"2026-10-12T18:0{i}:00") for i, r in enumerate(runs(*("VALIDATED",) * 4, "ERROR"))]
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))
    assert status.compute(status.load_records(path)["sha256:x"], RULES).failures == 1
    (tmp_path / "void.jsonl").write_text(json.dumps({"id": SID, "started": "2026-10-12T18:04:00",
                                                     "reason": "checks ran against another cluster"}) + "\n")
    st = status.compute(status.load_records(path)["sha256:x"], RULES)
    assert (st.runs, st.failures, st.status) == (4, 0, "draft")
