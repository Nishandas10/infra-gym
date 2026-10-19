"""gym/faults/flags.py app.flag_targeting: a targeting rule added while the flag still reads "off" at a glance."""
from __future__ import annotations

import json

import pytest

from gym.faults import flags

CONFIG = json.dumps({"flags": {"paymentFailure": {"state": "ENABLED", "defaultVariant": "off",
                                                  "variants": {"off": 0, "90%": 0.95}}}})
RULE = {"if": [{">=": [{"var": "$flagd.timestamp"}, "$SINCE"]}, "90%", "off"]}


def test_the_rule_is_added_and_the_default_stays():
    f = json.loads(flags.with_targeting(CONFIG, "paymentFailure", RULE))["flags"]["paymentFailure"]
    assert f["defaultVariant"] == "off" and f["targeting"] == RULE


def test_an_unknown_flag_is_refused():
    with pytest.raises(KeyError):
        flags.with_targeting(CONFIG, "noSuchFlag", RULE)


def test_inject_writes_the_live_file_and_reverts_it(monkeypatch):
    live = {"text": CONFIG}
    monkeypatch.setattr(flags, "read_config", lambda: live["text"])
    monkeypatch.setattr(flags, "write_config", lambda text: live.update(text=text))
    monkeypatch.setattr(flags, "evaluate", lambda flag, context=None: {"variant": "90%"})
    reverts = []

    class Undo:
        def on_revert_exec(self, target, cmd, container=None, stdin=None):
            reverts.append(stdin)
    monkeypatch.setattr(flags.time, "time", lambda: 1_000_000)
    flags.flag_targeting({"flag": "paymentFailure", "expect_variant": "90%", "since_s": 600, "targeting": RULE},
                         Undo(), None)
    rule = json.loads(live["text"])["flags"]["paymentFailure"]["targeting"]
    assert rule["if"][0][">="][1] == 1_000_000 - 600          # "$SINCE" became the rollout start
    assert reverts == [CONFIG]                                # revert writes the original file back
