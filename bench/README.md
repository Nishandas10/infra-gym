# Agent benchmark

Runs AI models (any OpenAI-compatible API, e.g. OpenRouter) against the gym's scenarios
and builds a leaderboard. Built on the gym library: it uses `faults.inject/revert`,
`harness.poll` and `checks` exactly as `scripts/validate_scenario.py` does.

## One episode

world healthy -> snapshot -> baseline PASS -> inject -> verifier FAIL -> the model works in a
sandbox -> verifier PASS, and PASS again after `hold_s` -> every user journey passes
(`verifier.invariants`, `shop_health`) -> the checks pass again after restarting
`verifier.durability` -> revert the fault exactly -> restore anything else the model changed
(`world.py`) -> world healthy again. A row passes only if all of these hold and no forbidden
action was taken (`invariants_ok` and `durable` are recorded; `durable` is null when the
scenario has nothing to restart).

A shop check that still passed during the fault but fails after the agent counts as **made worse** only if the
agent changed something: a change command (`safety.is_mutating`: `kubectl apply/patch/set/delete/run/...`, `rollout
undo/restart`, SQL and Valkey writes; `auth can-i` and dry runs do not count), a collateral change, a restart or a
touched decoy. Otherwise the fault itself spread (a cascade, or intermittent damage), which is recorded as
`fault_spread` and not blamed on the agent.


In an incident whose layers show one after another (driver `sequential-layers`), a correct fix of the first layer
exposes the next by design (103: fixing cart's port turns "connection refused" into NOAUTH). Checks that break after an
agent whose changes stayed on the fault's own objects (no collateral change, no unrelated restart, no decoy touched)
are recorded as `revealed`, not as made worse; pass/fail is unchanged. Rows graded before this rule (2026-10-19) get
it applied when the reports read them. Kafka's own admin commands that change the broker (`kafka-configs --alter`,
`kafka-topics --create/--delete`, `kafka-consumer-groups --reset-offsets ... --execute`) count as changes too (TTD,
changes made, made worse); `--describe`, `--list` and dry runs do not.

## Fairness and safety rules

- **Chaos Mesh scenarios are excluded** (`bench_eligible: false` in their templates). Their only
  fix is deleting the chaos object, which an SRE never does in a real incident.
- **Only validated scenarios run** (`only_validated` in `config.yaml`): at least 5 validation runs of
  the scenario's current version with at most 1 failure (`gym/core/status.py`). Suite members must also have
  passed a **long-hold** run: a do-nothing agent still fails after the agent's whole wall-clock budget
  (`scripts/validate_scenario.py --suite S --long-hold`), so no scenario can heal itself mid-episode.
- **Every result row records the suite and the scenario's `content_hash`** (see Suites), so results can be tied to the exact
  version of the scenario that ran.
- **The model works in a container that cannot see this repo**, so it can't read reference
  solutions, checks or the undo log.
- **Its Kubernetes account** (`sandbox_up.sh`) can operate the app namespace (`app_namespace` in `worlds/k8s-shop.yaml`, `default`) and `kube-system`, nodes,
  namespace labels and admission webhooks. It has **no access to `gym-system`** (the
  verifier's probe pods) or `chaos-mesh`, and cannot create or change admission policies (it may list and delete mutating admission policies and their bindings, as an SRE removes a bad one).
- **No pod in the app namespace may run on the control-plane node.** `sandbox_up.sh` installs a
  ValidatingAdmissionPolicy (`gym-no-control-plane`) that rejects pods pinned there by `nodeName` and, for pods the
  scheduler places, tolerations of the control-plane taint (a wildcard toleration included). A pod pinned to a worker
  may tolerate anything. `preflight` checks it with server-side dry runs.
- **The agent cannot reach the machine running the benchmark.** Admission policies (`gym-agent-host-*`) stop it from
  giving any pod host access (privileged, host network/PID/IPC, hostPath, SYS_ADMIN), directly or through a workload
  template, from changing the code of a workload that already has it (kube-proxy may still be rescheduled, not given
  another image), and from attaching debug containers to such pods; so `kubectl debug node/<worker>` is refused. In
  `kube-system` it cannot exec into pods. Its sandbox reaches only the kind network: no internet and no cloud metadata
  server (`sandbox_firewall.sh`, run by `sandbox_up.sh` through `sudo -n`). `preflight` checks all of it.
- **Every model gets the same system prompt, tools, temperature and per-scenario budget**
  (`budget` in spec.yaml). The system prompt states the command budget (`max_steps`), and the output of the command
  that leaves 5 commands is followed by `[5 of your N commands left]`.
- **Prompt versions.** Everything the agent is told (system prompt, the reminder when it replies without a command,
  the budget note, the request for a report) has a version, `PROMPT_VERSION` in `bench/rows.py`, recorded in every row
  as `prompt_version`. Version 1 (rows without the field, until 2026-10-15) did not mention the budget; version 2
  states it and adds the reminder; version 3 (2026-10-17) adds "if nothing needs fixing, change nothing and
  explain why", for false alarms. Results of different prompt versions are not comparable: suite reports count only
  the current version, and a test pins the texts' hash to it, so a prompt change must bump the version.
- **Forbidden actions** fail the episode even if the checks pass. Each scenario lists them
  (`verifier.forbidden`, from `templates/defaults.yaml`; meanings in `templates/taxonomy.yaml`):
  deleting a namespace, scaling one of the shop's own workloads to zero, disabling monitoring,
  removing a health probe the healthy world has, and changing anything in `gym-system`.
  `safety.py` detects the first and last from the agent's commands (an attempt counts) and the
  others from workload state before and after the agent, so the fault's own changes are never
  blamed on it.
- **`world.py` snapshots and restores everything else the model could change.** This covers
  objects in `default`, CoreDNS and kube-proxy, node labels, cordons and taints, namespace
  labels and webhooks. One episode can't leak into the next.
- **Known trait of the world (v1): the Kafka broker's memory is tight.** A Kafka CLI (`kafka-configs.sh`,
  `kafka-consumer-groups.sh`, ...) run inside the broker's pod inherits its `KAFKA_HEAP_OPTS=-Xmx400M` and the OTel Java
  agent, and the two JVMs together exceed the pod's 1Gi limit: the broker is OOMKilled (exit 137), and Kafka clients
  such as checkout's producer can stay wedged after it restarts. The CLI works with a small heap (`env
  KAFKA_HEAP_OPTS='-Xmx96M -Xms16M' JAVA_TOOL_OPTIONS= ...`, as the reference fixes do). It concerns the Kafka
  scenarios (031, 082, 083, 118, 130); an agent that sees the OOM can recover, and the world check before the next
  episode resets the shop if it did not.

## Suites

Models are compared on **suites**: frozen, versioned lists of `{id, hash}` pairs, where `hash` is the
instance's `content_hash` when the suite was frozen (`gym/core/suites.py`, made by `scripts/make_suite.py`).

| Suite | Where | Instances | What for |
|---|---|---|---|
| `bench-v1-dev` | `suites/` (public) | 20 standard | development and published results |
| `hard-v1` | `suites/` (public) | the 16 Hard scenarios | the Hard tier |
| `lite` | `suites/` (public) | 10 fast standard | smoke runs and onboarding |
| `bench-v1-test` | `private/suites/` (private) | 40 standard, 5/5 validated, at most 4 flag scenarios | held-out test; no results published |

All suites are graded at hint level `page` (symptoms only). `bench-v1-dev` and `lite` share no instance with
`bench-v1-test`. `private/` is a checkout of a separate private repository and is git-ignored here
(`INFRA_GYM_PRIVATE` points elsewhere); results of a private suite are written to `private/results/`, never to
`bench/results/`.

- `python bench/agent_bench.py run --suite bench-v1-dev` refuses to start if any member's current `content_hash`
  differs from the suite (the scenario changed after the suite was frozen) or a member is no longer validated.
  Fix it by freezing a new suite version, not by editing the suite file: `python scripts/make_suite.py --refreeze S`
  keeps the members, takes their current hashes and records which changed (each must still qualify).
- `python scripts/make_suite.py --check` verifies every suite against the current instances (CI runs the same check
  in `tests/test_suites.py`).
- `python scripts/make_suite.py --name X --n N [--split train|hard] [--clean] [--cap fix_type=flag:4] [--exclude S] [--fastest]`
  freezes a new suite: seeded, proportional to layer sizes, preferring new symptoms and fix types within a layer,
  validated instances only (`--clean`: no failed validation run). It replaces the old `pick` command.

## Commands

    python bench/agent_bench.py preflight    # cluster, restore logic, agent permissions
    python bench/agent_bench.py smoke        # API key, model IDs, tool calling
    python bench/agent_bench.py run --suite S [--limit N] [--only ID] [--model ID] [--attempts N] [--attempt N] [--retry-errors] [--rerun] [--hint-level page|ticket|hinted] [--api-key-env NAME] [--min-seconds-between-calls S] [--shard i/N] [--max-cost USD]
    python bench/leaderboard.py --suite S [--common]

`--shard i/N` (one worker per cluster, each with its own `KUBECONFIG`, all started together) splits the episodes over
clusters; `--max-cost USD` stops a worker once its episodes cost that much. An episode's cost is what the provider
billed when it says so (OpenRouter's `usage.cost`, which follows the host that served each reply; recorded as
`cost_billed_usd`), else its tokens at the `config.yaml` prices. Shares are taken from the whole plan before finished
episodes are dropped, so workers that start at different times never overlap.

One job per cluster: `run`, `oracle`, `preflight`, `scripts/validate_scenario.py` and `injectors/inject.py` hold the
cluster's lock (`gym/lock.py`, machine-wide, keyed by the kube context) while they run; a second one on the same
cluster refuses to start and names the job that holds it.

For a program that launches runs (the web app's runner), with nothing graded differently:

    python bench/agent_bench.py run --suite S --model M --config job/models.yaml --events job/events-1.jsonl --stop-file job/STOP --job ID [--shard i/N --max-cost USD]
    python bench/agent_bench.py status --json    # clusters (lock holder, undo logs, sandbox, nodes, free), suites, models; read-only, no lock
    python bench/export.py --suite S [--mode M] [--out F]   # leaderboard, scoreboard, breakdowns, calibration, catalog as JSON

- `--config PATH`: a YAML file with a `models:` list (entries as in `config.yaml`); its other top-level keys override
  `config.yaml`'s. Models added outside the repo keep `git_dirty: false`; every row records `model_config_hash` (the
  entry's hash) and `price`, which the reports use when `config.yaml` has no price for the model.
- `--events PATH`: live events, one JSON line each (`bench/events.py` lists them: run_start, episode_start, injected,
  agent_start, step, agent_done, verdict, cleanup, episode_end, run_end with its reason). `seq` continues when a
  resumed run appends to the same file. Events report; the rows stay the record.
- `--stop-file PATH`: the run stops before its next episode once the file exists (the episode in flight finishes and
  is cleaned up); the same command resumes after the file is removed.
- `--job ID`: recorded as `job` in every row and event.

Without `--suite`, `run` uses every bench-eligible, validated scenario (`config.yaml` include/exclude apply). `--set`
still works as an alias of `--suite` for one release; `.txt` set files are no longer accepted.

The agent gets the suite's hint level (`page`) unless `--hint-level` says otherwise; such episodes are recorded but
do not count in the suite's reports. Every result row records:

- `suite`, `suite_version`, `suite_hash` (fingerprint of the suite's name, version, hint level and members)
- `content_hash`, `validation_hash`, `template_version` and `tags` of the instance, `hint_level` and `prompt_version`
- `episode` (a unique id), `git_sha` and `git_dirty` (code changes outside the results folders)

Results: `bench/results/results.jsonl` (one line per episode), plus full transcripts in
`bench/results/transcripts/<model>/<scenario>__a<N>__<episode>.json`. Re-running `run` resumes where it stopped: an
episode is done when that model and attempt already ran this exact instance (`content_hash`) at this hint level with
the current prompt version.
`--rerun --only a,b` runs those scenarios again even if finished; the newest row of an episode replaces the older one
in every report. `--attempt N` limits a run to attempt N (with `--rerun --only`: re-run just that attempt).

Every report (`leaderboard.py`, `scoreboard.py`, `judge.py`, `cost.py`, `passk.py`, `show.py`, `quality_card.py`)
takes `--suite S` and then counts only rows whose `(scenario, content_hash)` is a member of the suite at its hint
level and the current prompt version (`bench/rows.py`), so a row counts for every suite that holds exactly the
instance it ran. `--any-version` matches by id only, for results from before suites or older prompts; those numbers
are labelled as not pinned. Leaderboard,
scoreboard and report break pass rates down by the tag axes layer, fix type and drivers.

## Claude and cost

- `python bench/agent_bench.py run --suite bench-v1-dev --model claude --attempts 3` runs only matching models,
  with 3 attempts (overrides config).
- Claude runs on the native API when `base_url` is `https://api.anthropic.com`: `effort` is sent as
  `output_config.effort`, the conversation is prompt-cached automatically, and thinking blocks are passed back unchanged.
  Temperature is not sent to Claude (thinking models use their default).
- `python bench/cost.py --project 90` prints cost per model from the recorded tokens (prices from config.yaml).

## Providers

- **Claude**: native Anthropic API (`base_url: https://api.anthropic.com`, key `ANTHROPIC_API_KEY`).
- **Gemini**: native Gemini API (`base_url: https://generativelanguage.googleapis.com/v1beta`, key `GEMINI_API_KEY`
  from Google AI Studio). `thinking_level` is sent as `thinkingConfig.thinkingLevel`; Gemini's reply parts (with thought
  signatures) are sent back unchanged; implicit caching is automatic above 4,096 prompt tokens and cached/thinking tokens
  are recorded exactly.
- **DeepSeek**: native DeepSeek API (`base_url: https://api.deepseek.com`, key `DEEPSEEK_API_KEY`), OpenAI-compatible.
  Thinking mode returns `reasoning_content`, which is sent back with every assistant message (DeepSeek rejects a
  request with tools that leaves it out). Caching is automatic; hits are recorded from `prompt_cache_hit_tokens`.
  Peak hours (weekdays 01:00-04:00 and 06:00-10:00 UTC) cost double, but `cost.py` uses the off-peak prices in
  `config.yaml`, so run long suites off-peak.
- **Free tiers**: put the key in `.env` under its own name and pass it for one run, e.g.
  `run --model gemini --api-key-env GEMINI_FREE_API_KEY --min-seconds-between-calls 7`. The config is not edited, so
  rows keep `git_dirty: false`. Rate-limit errors (429) wait longer; after 3 episodes in a row fail at the API (daily
  quota) the model is skipped, and `--retry-errors` picks those episodes up the next day. Google may use free-tier
  prompts and replies to improve its products: use free keys for public suites only, never for `bench-v1-test`.
- **Everything else**: OpenRouter (`OPENROUTER_API_KEY`). Each episode sends one `session_id`, so every step stays on the
  same provider and its prompt cache.

## Reading, judging and scoring

    python bench/show.py                         # list every finished episode
    python bench/show.py <scenario> [--model m]  # what the model did, step by step (thinking, commands, outputs, timing)
    python bench/judge.py run --suite S [--dry-run] [--model m] [--judge id]   # grade root-cause reports vs the ground truth
    python bench/judge.py audit --suite S --n 12 # grade a sample yourself, blind, to measure judge agreement
    python bench/judge.py report --suite S # diagnosis table + judge-vs-human agreement (Cohen's kappa)
    python bench/scoreboard.py --suite S [--common]   # Diag. / Mit. / E2E / TTD / TTM / Tokens / Clean / Worse / $ per solve
    python bench/calibration.py --suite S [--judge id] # per scenario: each model's passes, band (easy/medium/hard), signal

- The judge never changes PASS/FAIL; the verifier decides that. It sees the answer key, the incident prompt and the
  model's report only (no model name, no PASS/FAIL), votes 2-3 times, and grades correct / partial / wrong / missing.
  Rubric v2 also grades **location** (named the faulty object(s)) and **mechanism** (said what is wrong with them)
  separately; grades from rubric v1 are kept but not mixed with v2 (`--regrade` re-grades old episodes).
- TTD = seconds from the agent's start to its first command that changes the cluster. TTM = seconds from the agent's start
  until the verifier sees the service working (checked once the agent stops). Both include model/API latency.
- Answer keys: `scenarios/<id>/judge_key.md` if present, else the scenario's `ground_truth` (root causes, explanation,
  evidence, noise) plus the reference fix, rendered by `gym.core.generate.answer_key`.
