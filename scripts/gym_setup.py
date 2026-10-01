"""One-time (idempotent) setup of the gym's helper pods in the gym-system namespace.

usage: python scripts/gym_setup.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym import toolbox  # noqa: E402

if __name__ == "__main__":
    print("Deploying gym-system helper pods (probe + kafka tools)...")
    toolbox.ensure()
    print("Ready.")
