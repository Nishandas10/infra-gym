"""The undo log is kept per cluster (gym/undo.py)."""
from __future__ import annotations

import json

from gym import undo


def test_each_cluster_has_its_own_undo_log(tmp_path, monkeypatch):
    """Running one scenario on two clusters at once must not let one run revert the other's fault
    (wl-nodeselector-018, 2026-10-14: a shared log left two clusters on the fault's Recreate strategy)."""
    monkeypatch.setattr(undo, "STATE_DIR", tmp_path)
    monkeypatch.setenv("KUBECONFIG", "/home/u/.kube/gym/ai-gym")
    undo.UndoLog("wl-nodeselector-018").add({"op": "delete", "kind": "pod", "name": "x", "ns": "default"})
    monkeypatch.setenv("KUBECONFIG", "/home/u/.kube/gym/ai-gym-2")
    assert not undo.UndoLog("wl-nodeselector-018").active
    monkeypatch.setenv("KUBECONFIG", "/home/u/.kube/gym/ai-gym")
    assert undo.UndoLog("wl-nodeselector-018").active
    assert (tmp_path / "ai-gym" / "wl-nodeselector-018.json").exists()


def test_a_log_from_before_per_cluster_logs_is_still_found(tmp_path, monkeypatch):
    monkeypatch.setattr(undo, "STATE_DIR", tmp_path)
    monkeypatch.delenv("KUBECONFIG", raising=False)
    (tmp_path / "pay-fail-006.json").write_text(json.dumps([{"op": "delete", "kind": "pod", "name": "x", "ns": "d"}]))
    assert undo.UndoLog("pay-fail-006").active
