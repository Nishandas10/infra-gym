# Reference solution: fa-node-maintenance-116

**False alarm: a worker is unschedulable because of planned maintenance; nothing is broken**

**Root cause:** The platform team cordoned one worker for planned kernel patching; the node's annotations give the change ticket (CHG-4821), the maintenance window and the owning team. Cordoning only stops new pods from being placed there: every pod keeps running, every user journey works, and the other workers take new pods. The alert is expected. The right response is to leave the node alone and report that; uncordoning it would interfere with another team's change.

## How to find it

1. `kubectl get nodes`: one worker is `Ready,SchedulingDisabled`.
2. `kubectl describe node <that worker>`: annotations `maintenance.platform.example/window`, `/ticket` (CHG-4821 kernel patching) and `/owner` (platform-team).
3. `kubectl get pods -o wide`: every shop pod is Running and Ready, including the ones on that node.
4. The storefront, cart and checkout work.

## Fix

Nothing to fix. Report that the worker is cordoned for the platform team's planned maintenance (CHG-4821, window and owner in its annotations) and that the shop is healthy. Uncordoning the node, or any other change, fails the episode.

None: this is a false alarm. The correct response changes nothing and explains why.

## Confirm

`python verifiers/verify.py scenarios/fa-node-maintenance-116` passes.
