"""bench/agent_bench.py run_agent, offline: token accounting per API and the reasoning passback DeepSeek needs."""
from __future__ import annotations

import copy
import pathlib
import sys
from types import SimpleNamespace as NS

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import agent_bench as ab  # noqa: E402


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
