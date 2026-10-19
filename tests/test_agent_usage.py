"""bench/agent_bench.py run_agent, offline: token accounting per API and the reasoning passback DeepSeek needs."""
from __future__ import annotations

import copy
import pathlib
import sys
from types import SimpleNamespace as NS

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import agent_bench as ab  # noqa: E402
import rows as R  # noqa: E402


class Extra(NS):
    """An SDK object whose unknown response fields sit in model_extra, like the openai package's models."""

    def __init__(self, model_extra=None, **kw):
        super().__init__(model_extra=model_extra or {}, **kw)


def tool_call(cid, command):
    return Extra(id=cid, function=NS(name="run_shell", arguments=f'{{"command": "{command}"}}'))


def reply(content="", calls=None, msg_extra=None, usage=None, resp_extra=None):
    msg = Extra(content=content, tool_calls=calls, model_extra=msg_extra)
    return Extra(choices=[NS(message=msg)], usage=usage, model_extra=resp_extra)


def test_usage_counts_per_api():
    # DeepSeek's own API: cache hits in prompt_cache_hit_tokens (an extra field), prompt_tokens includes them
    deepseek = Extra(prompt_tokens=1000, completion_tokens=50, prompt_tokens_details=None,
                     prompt_cache_hit_tokens=800, prompt_cache_miss_tokens=200)
    assert ab.usage_counts(deepseek) == (1000, 50, 800, 0)
    # OpenRouter: cached and written tokens in prompt_tokens_details
    openrouter = Extra(prompt_tokens=1000, completion_tokens=50,
                       prompt_tokens_details=Extra(cached_tokens=600, model_extra={"cache_write_tokens": 300}))
    assert ab.usage_counts(openrouter) == (1000, 50, 600, 300)
    # a dict from a provider the SDK did not type
    assert ab.usage_counts(Extra(prompt_tokens=10, completion_tokens=1,
                                 prompt_tokens_details={"cached_tokens": 4})) == (10, 1, 4, 0)
    # the Claude and Gemini adapters set cache_read / cache_write themselves
    assert ab.usage_counts(NS(prompt_tokens=900, completion_tokens=40, cache_read=500, cache_write=100)) == \
        (900, 40, 500, 100)
    assert ab.usage_counts(None) == (0, 0, 0, 0)


def test_a_bad_request_is_not_retried(monkeypatch):
    class BadRequest(Exception):
        status_code = 400
    calls = []

    def create(**kw):
        calls.append(kw)
        raise BadRequest("Error code: 400 - this API key is not scoped to a workspace")
    client = NS(chat=NS(completions=NS(create=create)))
    monkeypatch.setattr(ab.time, "sleep", lambda s: calls.append(("slept", s)))
    try:
        ab.chat(client, {"id": "m", "base_url": "http://model.invalid"}, [], 0.2)
    except BadRequest:
        pass
    assert len(calls) == 1                        # one call, no retry, no wait


def test_billed_cost_per_api():
    assert ab.billed_cost(Extra(prompt_tokens=10, completion_tokens=1, model_extra={"cost": 0.0123})) == 0.0123
    assert ab.billed_cost(Extra(prompt_tokens=10, completion_tokens=1)) == 0.0
    assert ab.billed_cost(NS(prompt_tokens=9, completion_tokens=4, cache_read=5, cache_write=0)) == 0.0
    assert ab.billed_cost(None) == 0.0


def test_an_episode_records_what_openrouter_billed(monkeypatch):
    usage = Extra(prompt_tokens=100, completion_tokens=10, prompt_tokens_details=None, model_extra={"cost": 0.25})
    replies = [reply(calls=[tool_call("c1", "kubectl get pods")], usage=usage), reply(content="done", usage=usage)]
    monkeypatch.setattr(ab, "chat", lambda client, ms, messages, temperature: replies.pop(0))
    monkeypatch.setattr(ab, "run_in_sandbox", lambda command: "ok")
    out = ab.run_agent(None, {"id": "x/y", "base_url": "https://openrouter.ai/api/v1"}, "The shop is down.",
                       max_steps=5, wall_s=60, temperature=0.2)
    assert out["cost_billed_usd"] == 0.5
    price = {"input": 1000, "output": 1000}           # the recorded bill wins over the configured price
    assert R.cost_usd({"tokens_in": 200, "cost_billed_usd": out["cost_billed_usd"]}, price) == 0.5
    assert R.cost_usd({"tokens_in": 1_000_000}, {"input": 1, "output": 1}) == 1.0


def test_reasoning_content_is_sent_back(monkeypatch):
    """Every request after a DeepSeek reply must carry that reply's reasoning_content (else the API returns 400)."""
    usage = Extra(prompt_tokens=100, completion_tokens=10, prompt_tokens_details=None, prompt_cache_hit_tokens=60)
    replies = [
        reply(calls=[tool_call("c1", "kubectl get pods")], msg_extra={"reasoning_content": "look at pods"},
              usage=usage),
        reply(content="Root cause: X. Fixed: Y.", msg_extra={"reasoning_content": "done"}, usage=usage),
    ]
    sent = []

    def chat(client, ms, messages, temperature):
        sent.append(copy.deepcopy(messages))
        return replies[len(sent) - 1]
    monkeypatch.setattr(ab, "chat", chat)
    monkeypatch.setattr(ab, "run_in_sandbox", lambda command: "pod/a Running")
    ms = {"id": "deepseek-v4-pro", "base_url": "https://api.deepseek.com"}
    out = ab.run_agent(None, ms, "The shop is down.", max_steps=5, wall_s=60, temperature=0.2)

    assert out["stop"] == "model_finished" and out["steps"] == 1
    assistant = [m for m in sent[1] if m["role"] == "assistant"]
    assert assistant[0]["reasoning_content"] == "look at pods"
    assert assistant[0]["tool_calls"][0]["id"] == "c1"
    assert (out["tokens_in"], out["tokens_out"], out["tokens_cache_read"]) == (200, 20, 120)
    assert out["providers"] == ["deepseek"]


def test_no_reasoning_field_for_other_providers(monkeypatch):
    replies = [reply(calls=[tool_call("c1", "kubectl get pods")]), reply(content="done")]
    sent = []

    def chat(client, ms, messages, temperature):
        sent.append(copy.deepcopy(messages))
        return replies[len(sent) - 1]
    monkeypatch.setattr(ab, "chat", chat)
    monkeypatch.setattr(ab, "run_in_sandbox", lambda command: "ok")
    ms = {"id": "stub", "base_url": "http://model.invalid"}
    out = ab.run_agent(None, ms, "The shop is down.", max_steps=5, wall_s=60, temperature=0.2)
    assert all("reasoning_content" not in m for m in sent[1])
    assert out["providers"] == []
