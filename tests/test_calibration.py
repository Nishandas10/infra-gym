"""bench/calibration.py: intervals, bands, signal and the per-scenario table, with stubbed rows and grades."""
from __future__ import annotations

import pathlib
import sys
from types import SimpleNamespace

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bench"))
import calibration as cal  # noqa: E402


def test_wilson_interval():
    assert cal.wilson(0, 0) is None
    lo, hi = cal.wilson(20, 20)
    assert hi == 1.0 and 0.83 < lo < 0.84          # 20/20 is not proof of 100%
    lo, hi = cal.wilson(1, 2)
    assert lo < 0.1 and hi > 0.9                    # two episodes say almost nothing


def test_band_and_signal():
    assert [cal.band(x) for x in (1, 2 / 3, 0.5, 1 / 3, 0)] == ["easy", "easy", "medium", "hard", "hard"]
    assert cal.signal([1, 1]) == "all_pass" and cal.signal([0, 0]) == "all_fail"
    assert cal.signal([1, 0]) == "separates" and cal.signal([0.5, 0.5]) == "same_partial"


def test_build(monkeypatch):
    def row(sid, model, attempt, passed, ep):
        return {"scenario": sid, "model": model, "attempt": attempt, "passed": passed, "status": "done", "episode": ep}

    rows = [row("a", "opus", 1, True, "e1"), row("a", "opus", 2, True, "e2"), row("a", "ds", 1, False, "e3"),
            row("b", "opus", 1, True, "e4"), row("b", "ds", 1, True, "e5"),
            {**row("b", "ds", 2, False, "e6"), "status": "error"}]          # not finished: not counted
    grades = {"e1": {"root_cause": "correct"}, "e3": {"root_cause": "correct"}, "e4": {"root_cause": "wrong"}}
    monkeypatch.setattr(cal.R, "load", lambda suite: rows)
    monkeypatch.setattr(cal, "judgments", lambda judge, results=None: grades)
    suite = SimpleNamespace(name="s", version=1, visibility="public",
                            instances=[SimpleNamespace(id=i, hash="h" + i) for i in "abc"])
    out = cal.build(suite, "judge")
    a, b, c = out["scenarios"]
    assert (a["models"]["opus"]["k"], a["models"]["opus"]["n"], a["models"]["ds"]["rate"]) == (2, 2, 0)
    assert (a["model_mean"], a["band"], a["signal"], a["provisional"]) == (0.5, "medium", "separates", True)
    assert a["understood_not_fixed"] == 1                                   # ds diagnosed it, did not fix it
    assert (b["signal"], b["band"], b["fixed_cause_wrong"], b["episodes"]) == ("all_pass", "easy", 1, 2)
    assert c["models"] == {} and out["not_run"] == ["c"]
    assert out["models"]["opus"]["pass_rate"] == 1 and out["models"]["ds"]["passed"] == 1
    assert out["models"]["opus"]["quadrants"] == {"fixed_understood": 1, "fixed_cause_wrong": 1}
    assert "| a | 0/1 | 2/2 | 50% | medium (provisional) | separates | C / C? |" in cal.markdown(out)
