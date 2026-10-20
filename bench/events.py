"""Live events of a benchmark run (`agent_bench.py run --events PATH`), one JSON object per line, for whoever watches
the run (the web app's runner tails the file). They only report what the run does; the result rows stay the record.

Every event has seq (1, 2, ... per file, continued when a resumed run appends to the same file), at (UTC), type, job,
shard and episode (None outside an episode), plus fields of its own:

  run_start      suite, suite_version, mode, models, attempts, episodes (this worker's plan), git_sha, pid
  episode_start  i, n, scenario, model, attempt
  injected       the fault is in place (the agent has not started yet)
  agent_start    max_steps, prompt
  step           step, t, cmd, changes, output (head), text (the model's text before its commands, first step of a turn)
  agent_done     stop, steps, agent_s, tokens_in, tokens_out, error
  verdict        status, passed, clean, safety, fixed, held, error
  cleanup        notes
  episode_end    status, passed, minutes, cost_usd (None without a price), spent_usd (this worker so far)
  run_end        reason (finished | stopped | spend_cap | error | interrupted), played, spent_usd, message
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_HEAD = 1500   # characters of a command's output kept in a step event
TEXT_HEAD = 1500


class Events:
    """Appends events to `path`; with no path every call is a no-op."""

    def __init__(self, path=None, job=None, shard=None):
        self.path = Path(path) if path else None
        self.job, self.shard, self.episode = job, shard, None
        self.seq = _last_seq(self.path) if self.path else 0

    def emit(self, type_, **fields):
        if not self.path:
            return
        self.seq += 1
        event = {"seq": self.seq, "at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "type": type_,
                 "job": self.job, "shard": self.shard, "episode": self.episode, **fields}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())


def _last_seq(path):
    """The seq of the file's last complete event (0 for a new file), so a resumed run continues the numbering."""
    if not path.exists():
        return 0
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - 65536))
        lines = f.read().decode("utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        try:
            return int(json.loads(line)["seq"])
        except (ValueError, KeyError, TypeError):
            continue
    return 0


def head(text, n):
    text = text or ""
    return text if len(text) <= n else text[:n] + f"\n[... {len(text) - n} more characters]"


NONE = Events()
