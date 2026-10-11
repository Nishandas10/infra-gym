# AI Infra Gym

Safe, resettable, realistic broken infrastructure for training and testing AI agents.

The "world" is the OpenTelemetry Demo (an online telescope shop, ~20 services)
on a 3-node kind cluster. Each **scenario** breaks it in one specific way, tells
the agent only the symptoms, and uses an out-of-band **verifier** that checks
real outcomes (pods, real user journeys, Kafka lag, telemetry) to decide
whether it was fixed. All scenarios are listed in [scenarios/CATALOG.md](scenarios/CATALOG.md).

## Layout

| Path | What it is |
|---|---|
| `templates/<family>/<id>/template.yaml` | **Where scenarios are written**: fault, prompts, verifier checks, reference fix, notes (spec v2, `gym/core/schema.py`) |
| `templates/defaults.yaml` | Defaults for every template (forbidden actions, tools, budget) |
| `scenarios/<id>/` | **Generated** from the template by `scripts/generate.py`: `spec.yaml` (resolved, content-hashed) and `reference_solution.md`. Do not edit. |
| `gym/` | Library: fault mechanisms (with exact undo), verifier checks, validation harness |
| `gym/core/` | Spec v2 schema and the template -> instance generator |
| `injectors/inject.py` | Inject any scenario (`--revert` undoes it exactly) |
| `injectors/toggle_flag.py` | Flip the demo's feature flags (works with demo 3.x) |
| `verifiers/verify.py` | Run a scenario's verifier (exit 0 = healthy) |
| `scripts/validate_scenario.py` | Prove scenarios work end to end; results in `results/validation.jsonl` |
| `scripts/reset_world.sh` | Re-sync the shop from Helm (pinned chart + `values-local.yaml`) |

## Setup (inside WSL, from the repo root)

```bash
source .venv/bin/activate
bash scripts/reset_world.sh          # shop, trimmed to fit a 6 GB WSL VM (see values-local.yaml)
bash scripts/install_chaos_mesh.sh   # needed by the chaos-* scenarios
python scripts/gym_setup.py          # helper pods in namespace gym-system (probe, kafka tools)
```

## Write or change a scenario

1. Edit (or add) `templates/<family>/<id>/template.yaml`. Files the fault reads (`chaos.yaml`)
   live in the same folder. A hand-written `reference_solution.md` there is used as is;
   otherwise it is generated from `reference.cause`, `reference.diagnose` and `reference.commands`.
2. If the change affects behaviour (fault, checks, fix, prompts, validation, budget), bump `version`.
3. `python scripts/generate.py` writes `scenarios/<id>/` and `scenarios/CATALOG.md`.
4. `python scripts/lint_scenarios.py` and `pytest`; then validate it on the cluster (below).

Each instance has a `content_hash` over everything that decides its behaviour, so results can
be tied to the exact version of a scenario they ran. Fault steps name their mechanism:
`k8s.*` (Kubernetes objects), `app.*` (the shop's feature flags), `runtime.*` (commands in
pods), `chaos.*` (Chaos Mesh); see `gym/faults/`.

## Offline tests (no cluster needed)

```bash
pip install -e ".[dev]"
ruff check .
python scripts/generate.py --check   # scenarios/ matches templates/
pytest
```

- `tests/test_inject_revert.py` injects and reverts every scenario against an in-memory fake
  cluster (`tests/fakes.py`) loaded from `tests/fixtures/world.json`, and checks the world is
  restored exactly.
- `tests/test_spec_snapshot.py` fails if any scenario's fault, checks, fix, validation timings,
  prompt or budget differ from `tests/golden/specs.json`. After an intended change, run
  `python scripts/snapshot_specs.py` and commit the updated snapshot with it.
- `tests/fixtures/world.json` is a snapshot of the healthy live world. Refresh it with
  `python scripts/dump_world_fixture.py` after changing the demo's Helm values.

CI runs the same steps on every push (`.github/workflows/ci.yml`).

## Play one scenario by hand

```bash
python verifiers/verify.py scenarios/pay-fail-006          # PASS: healthy
python injectors/inject.py scenarios/pay-fail-006          # break it
python verifiers/verify.py scenarios/pay-fail-006          # FAIL
# ...investigate and fix it yourself (or let an agent do it)...
python verifiers/verify.py scenarios/pay-fail-006          # PASS again?
python injectors/inject.py scenarios/pay-fail-006 --revert # always clean up exactly
```

`python scripts/run_episode.py scenarios/<id>` does reset -> baseline -> inject -> confirm broken.

## Validate scenarios

```bash
python scripts/validate_scenario.py scenarios/net-delay-002
python scripts/validate_scenario.py --all            # hours; stops if the cluster is left unhealthy
python scripts/generate.py --index                   # refresh scenarios/CATALOG.md with verdicts
```

Each run proves: baseline healthy -> inject -> verifier FAILs -> still FAILs for
a do-nothing agent -> the reference solution fixes it -> verifier PASSes ->
the world is restored exactly.

## What counts as a unique scenario

A scenario is unique only if its root-cause mechanism differs from every other
scenario's (the template's `mechanism`, enforced by `scripts/generate.py`).
Changing only numbers (memory size, latency, percentage), service names or
random seeds creates a variant, not a new scenario. Mechanisms that were tried
and dropped are listed in `templates/dropped.yaml`.
