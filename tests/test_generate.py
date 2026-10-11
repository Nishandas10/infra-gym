"""Templates -> instances: schema, freshness, content hash."""
from __future__ import annotations

import copy

import pytest
import yaml
from pydantic import ValidationError

from gym.core import generate
from gym.core.schema import Template

BUILT = generate.build_all()


def test_instances_are_up_to_date():
    assert not generate.stale(BUILT), "run: python scripts/generate.py"


def test_every_instance_has_a_template():
    assert sorted(BUILT) == sorted(p.name for p in generate.SCENARIOS.iterdir() if p.is_dir())


def _template(sid="wl-listen-port-drift-014"):
    tdir = next(d for d in generate.template_dirs() if d.name == sid)
    raw, _ = generate.load_template(tdir)
    return raw, generate.extra_files(tdir)


def test_hash_is_stable():
    raw, files = _template()
    d = generate.load_defaults()
    assert generate.resolve(raw, d, files)["content_hash"] == generate.resolve(copy.deepcopy(raw), d, files)["content_hash"]


@pytest.mark.parametrize("change", [
    lambda t: t["fault"]["steps"][0]["ops"][0].update(value="8082"),
    lambda t: t["verifier"]["checks"][0].update(repeat=5),
    lambda t: t["reference"]["commands"].append("true"),
    lambda t: t["task"]["prompts"].update(page="Checkout is broken. Find the cause and fix it."),
    lambda t: t.update(validation={"hold_s": 99}),
    lambda t: t.update(budget={"max_steps": 31, "wall_s": 900}),
])
def test_behaviour_change_changes_hash(change):
    raw, files = _template()
    d = generate.load_defaults()
    before = generate.resolve(raw, d, files)["content_hash"]
    changed = copy.deepcopy(raw)
    change(changed)
    assert generate.resolve(changed, d, files)["content_hash"] != before


@pytest.mark.parametrize("change, content_changes", [
    (lambda t: t["task"]["prompts"].update(page="Checkout is broken. Find the cause and fix it."), True),
    (lambda t: t["ground_truth"].update(explanation=t["ground_truth"]["explanation"] + " More detail."), True),
    (lambda t: t.update(budget={"max_steps": 31, "wall_s": 900}), True),
    (lambda t: t["tags"].update(symptom="partial"), False),   # tags describe a scenario, they don't change it
])
def test_non_runtime_change_keeps_validation_hash(change, content_changes):
    raw, files = _template()
    d = generate.load_defaults()
    before = generate.resolve(raw, d, files)
    changed = copy.deepcopy(raw)
    change(changed)
    after = generate.resolve(changed, d, files)
    assert after["validation_hash"] == before["validation_hash"]
    assert (after["content_hash"] != before["content_hash"]) == content_changes


@pytest.mark.parametrize("change", [
    lambda t: t["fault"]["steps"][0]["ops"][0].update(value="8082"),
    lambda t: t["verifier"]["checks"][0].update(repeat=5),
    lambda t: t["reference"]["commands"].append("true"),
    lambda t: t.update(validation={"hold_s": 99}),
])
def test_runtime_change_changes_validation_hash(change):
    raw, files = _template()
    d = generate.load_defaults()
    changed = copy.deepcopy(raw)
    change(changed)
    assert generate.resolve(changed, d, files)["validation_hash"] != generate.resolve(raw, d, files)["validation_hash"]


def test_notes_do_not_change_hash():
    raw, files = _template()
    d = generate.load_defaults()
    changed = copy.deepcopy(raw)
    changed["notes"] = ["an authoring note"]
    assert generate.resolve(changed, d, files)["content_hash"] == generate.resolve(raw, d, files)["content_hash"]


def test_extra_file_changes_hash():
    raw, files = _template("net-delay-002")
    d = generate.load_defaults()
    assert "chaos.yaml" in files
    changed = dict(files, **{"chaos.yaml": files["chaos.yaml"] + "\n# edited\n"})
    assert generate.resolve(raw, d, changed)["content_hash"] != generate.resolve(raw, d, files)["content_hash"]


@pytest.mark.parametrize("break_it, message", [
    (lambda t: t["fault"]["steps"][0].update(mechanism="k8s.no_such_thing"), "unknown mechanism"),
    (lambda t: t["verifier"]["checks"][0].update(type="no_such_check"), "unknown check type"),
    (lambda t: t.update(id="Bad_Id"), "id"),
    (lambda t: t.update(mechanism="no-slash"), "mechanism"),
    (lambda t: t.update(surprise=1), "Extra inputs"),
    (lambda t: t["verifier"].update(checks=[]), "at least 1"),
    (lambda t: t["reference"].update(commands=[]), "at least 1"),
    (lambda t: t["tags"].update(layer="kernel"), "taxonomy"),
    (lambda t: t["tags"].update(fix_type=["pray"]), "taxonomy"),
    (lambda t: t["tags"].update(drivers=["vibes"]), "taxonomy"),
    (lambda t: t["tags"].update(fix_type=[]), "at least 1"),
    (lambda t: t.pop("ground_truth"), "ground_truth"),
    (lambda t: t["ground_truth"].update(root_causes=[]), "at least 1"),
    (lambda t: t["ground_truth"]["root_causes"][0].update(component="payment"), "kind/name"),
    (lambda t: t.update(family="workload"), "Extra inputs"),
])
def test_schema_rejects(break_it, message):
    raw, _ = _template()
    bad = copy.deepcopy(raw)
    break_it(bad)
    with pytest.raises(ValidationError, match=message):
        Template.model_validate(bad)


def test_answer_key_names_every_root_cause_and_noise():
    inst = yaml.safe_load(BUILT["hard-masked-second-fault-107"]["spec.yaml"])
    key = generate.answer_key(inst)
    for rc in inst["ground_truth"]["root_causes"]:
        assert rc["component"] in key
    for noise in inst["ground_truth"].get("red_herrings", []):
        assert noise in key
    assert "NOT the cause" in key


def test_template_folder_is_its_layer():
    for tdir in generate.template_dirs():
        raw, model = generate.load_template(tdir)
        assert tdir.parent.name == model.tags.layer


def test_instance_header_and_resolved_defaults():
    text = BUILT["wl-listen-port-drift-014"]["spec.yaml"]
    assert text.startswith("# GENERATED by scripts/generate.py")
    inst = yaml.safe_load(text)
    defaults = generate.load_defaults()
    assert inst["verifier"]["forbidden"] == defaults.forbidden
    assert inst["budget"] == defaults.budget.model_dump()
    assert inst["instance_of"] == {"template": "wl-listen-port-drift-014", "version": 1, "params": {}}
