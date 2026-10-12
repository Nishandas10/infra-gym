"""Infra Gym library: fault injection, verification and validation for scenarios.

Layout:
  settings.py  world settings: app namespace, worker nodes... (worlds/*.yaml)
  kube.py      kubectl helpers and JSON-pointer utilities
  undo.py      per-scenario undo log, so every injection can be reverted exactly
  toolbox.py   helper pods in the gym-system namespace (HTTP probe, Kafka tools)
  checks.py    verifier checks (outside evidence only)
  faults/      fault mechanisms, looked up by each fault step's mechanism
  spec.py      loading scenario specs
  harness.py   the validate loop: baseline -> inject -> FAIL -> fix -> PASS -> restore
"""
