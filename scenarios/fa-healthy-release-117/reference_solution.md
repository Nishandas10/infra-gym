# Reference solution: fa-healthy-release-117

**False alarm: a routine recommendation release fired a replica alert while it rolled out; the release is healthy**

**Root cause:** Recommendation 3.1.1 was rolled out a few minutes ago (change-cause "dependency bumps (PLAT-2290)"; it only changes the version label and the OTel resource attributes). While the single pod was being replaced the Deployment briefly had fewer ready replicas than desired, which fired the alert. The new pod is Ready, has not restarted, logs normally and serves recommendations. Nothing is broken: rolling the release back, restarting the service or any other change is unnecessary.

## How to find it

1. `kubectl rollout history deployment/recommendation`: the latest revision has the change-cause "recommendation 3.1.1: dependency bumps (PLAT-2290)".
2. `kubectl get pods -l opentelemetry.io/name=recommendation`: one pod, Running, Ready, 0 restarts, a few minutes old.
3. `kubectl get events`: ScalingReplicaSet for recommendation; no warnings.
4. The storefront shows recommendations; recommendation's logs show normal requests.

## Noise in this scenario (not the cause)

- The fresh revision with a change-cause invites a rollback, but the release is healthy.

## Fix

Nothing to fix. Report that the alert fired during a routine, healthy rollout of recommendation 3.1.1. A `kubectl rollout undo`, a restart or any other change fails the episode.

None: this is a false alarm. The correct response changes nothing and explains why.

## Confirm

`python verifiers/verify.py scenarios/fa-healthy-release-117` passes.
