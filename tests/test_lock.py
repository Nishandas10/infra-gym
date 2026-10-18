"""gym/lock.py: one job per cluster."""
from __future__ import annotations

import pytest

from gym import lock


@pytest.fixture
def lockdir(tmp_path, monkeypatch):
    monkeypatch.setattr(lock, "LOCK_DIR", tmp_path)
    yield tmp_path
    while lock._held:
        lock._held.pop().close()


def test_a_second_job_on_the_same_cluster_is_refused(lockdir):
    assert lock.hold_cluster("validate_scenario", context="kind-ai-gym") == "kind-ai-gym"
    with pytest.raises(SystemExit) as e:
        lock.hold_cluster("agent_bench run", context="kind-ai-gym")
    assert "kind-ai-gym is in use (validate_scenario, pid" in str(e.value)


def test_other_clusters_are_free(lockdir):
    lock.hold_cluster("agent_bench oracle", context="kind-ai-gym")
    assert lock.hold_cluster("agent_bench oracle", context="kind-ai-gym-2") == "kind-ai-gym-2"


def test_the_lock_goes_with_the_job(lockdir):
    lock.hold_cluster("agent_bench run", context="kind-ai-gym-3")
    lock._held.pop().close()                      # the process ended
    assert lock.hold_cluster("agent_bench run", context="kind-ai-gym-3") == "kind-ai-gym-3"
