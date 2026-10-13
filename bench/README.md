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

## Fairness and safety rules

- **Chaos Mesh scenarios are excluded** (`bench_eligible: false` in their templates). Their only
  fix is deleting the chaos object, which an SRE never does in a real incident.
- **Only validated scenarios run** (`only_validated` in `config.yaml`): at least 5 validation runs of
  the scenario's current version with at most 1 failure (`gym/core/status.py`).
- **Every result row records the scenario's `content_hash`**, so results can be tied to the exact
  version of the scenario that ran.
- **The model works in a container that cannot see this repo**, so it can't read reference
  solutions, checks or the undo log.
- **Its Kubernetes account** (`sandbox_up.sh`) can operate the app namespace (`app_namespace` in `worlds/k8s-shop.yaml`, `default`) and `kube-system`, nodes,
  namespace labels and admission webhooks. It has **no access to `gym-system`** (the
  verifier's probe pods) or `chaos-mesh`.
- **Every model gets the same system prompt, tools, temperature and per-scenario budget**
  (`budget` in spec.yaml).
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

## Commands

    python bench/agent_bench.py preflight    # cluster, restore logic, agent permissions
    python bench/agent_bench.py smoke        # API key, model IDs, tool calling
    python bench/agent_bench.py run [--limit N] [--only ID] [--model ID] [--retry-errors] [--hint-level page|ticket|hinted]
    python bench/leaderboard.py

The agent gets the scenario's `page` prompt (symptoms only) unless `--hint-level` says otherwise;
every result row records the hint level, the scenario's layer, tier and `content_hash`.

Results: `bench/results/results.jsonl` (one line per episode), plus full transcripts in
`bench/results/transcripts/<model>/<scenario>__a<N>.json`. Re-running `run` resumes where it stopped.

## Scenario sets, Claude, and cost

- `python bench/agent_bench.py pick --n 30 --seed 1` writes `bench/sets/set30.txt`, a fixed, layer-balanced set.
  Same seed = same set, so every model can be compared on exactly the same scenarios.
- `python bench/agent_bench.py run --set bench/sets/set30.txt --model claude --attempts 3` runs only that set,
  only matching models, with 3 attempts (overrides config).
- Claude runs on the native API when `base_url` is `https://api.anthropic.com`: `effort` is sent as
  `output_config.effort`, the conversation is prompt-cached automatically, and thinking blocks are passed back unchanged.
  Temperature is not sent to Claude (thinking models use their default).
- `python bench/cost.py --project 90` prints cost per model from the recorded tokens (prices from config.yaml).
- `python bench/leaderboard.py --set bench/sets/set30.txt --common` compares models only on scenarios all of them finished.

## Providers

- **Claude**: native Anthropic API (`base_url: https://api.anthropic.com`, key `ANTHROPIC_API_KEY`).
- **Gemini**: native Gemini API (`base_url: https://generativelanguage.googleapis.com/v1beta`, key `GEMINI_API_KEY`
  from Google AI Studio). `thinking_level` is sent as `thinkingConfig.thinkingLevel`; Gemini's reply parts (with thought
  signatures) are sent back unchanged; implicit caching is automatic above 4,096 prompt tokens and cached/thinking tokens
  are recorded exactly.
- **Everything else**: OpenRouter (`OPENROUTER_API_KEY`). Each episode sends one `session_id`, so every step stays on the
  same provider and its prompt cache.

## Reading, judging and scoring

    python bench/show.py                         # list every finished episode
    python bench/show.py <scenario> [--model m]  # what the model did, step by step (thinking, commands, outputs, timing)
    python bench/judge.py run --set S [--dry-run] [--model m] [--judge id]   # grade root-cause reports vs the ground truth
    python bench/judge.py audit --set S --n 12   # grade a sample yourself, blind, to measure judge agreement
    python bench/judge.py report --set S         # diagnosis table + judge-vs-human agreement (Cohen's kappa)
    python bench/scoreboard.py --set S [--common]   # Diag. / Mit. / E2E / TTD / TTM / Tokens / Clean / Worse / $ per solve

- The judge never changes PASS/FAIL; the verifier decides that. It sees the answer key, the incident prompt and the
  model's report only (no model name, no PASS/FAIL), votes 2-3 times, and grades correct / partial / wrong / missing.
  Rubric v2 also grades **location** (named the faulty object(s)) and **mechanism** (said what is wrong with them)
  separately; grades from rubric v1 are kept but not mixed with v2 (`--regrade` re-grades old episodes).
- TTD = seconds from the agent's start to its first command that changes the cluster. TTM = seconds from the agent's start
  until the verifier sees the service working (checked once the agent stops). Both include model/API latency.
- Answer keys: `scenarios/<id>/judge_key.md` if present, else the scenario's `ground_truth` (root causes, explanation,
  evidence, noise) plus the reference fix, rendered by `gym.core.generate.answer_key`.
