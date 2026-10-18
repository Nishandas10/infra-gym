# Reference solution: kubelet-stopped-129

**The kubelet on a worker node stopped; the node goes NotReady and its pods lose their endpoints**

**Root cause:** The kubelet service on one worker node was stopped; the node itself (its container runtime and the containers already running) is still up. Without the kubelet the node posts no status: after about 40 s the node controller marks it NotReady, taints it node.kubernetes.io/unreachable, and marks its pods not ready, which removes them from their Services' endpoints, so the services running there fail. After the 300 s toleration the pods are evicted and recreated on the other worker; they stay Terminating on the dead node. Commands that go through the kubelet (kubectl logs/exec on that node's pods) fail with connection refused on port 10250. The fix is to start the kubelet on the node again (systemctl start kubelet on the machine), which needs access to the node itself.

## How to find it

1. `kubectl get nodes`: one worker NotReady; `kubectl describe node <it>`: conditions Unknown, "Kubelet stopped posting node status", taints node.kubernetes.io/unreachable.
2. `kubectl get pods -o wide`: that node's pods not ready, later Terminating, with replacements on the other worker.
3. `kubectl logs` or `kubectl exec` on a pod of that node: dial tcp <node-ip>:10250: connect: connection refused.

## Noise in this scenario (not the cause)

- The failing shop services are victims; their own configuration is unchanged.

## Fix

Start the kubelet on the affected node again (on the machine: `systemctl start kubelet`, then check `systemctl status kubelet` and its journal). The node turns Ready within a minute and its pods recover. From inside the cluster with the on-call permissions this cannot be fixed; the right answer names the node and its kubelet.

```bash
docker exec "$(kubectl get nodes -l '!node-role.kubernetes.io/control-plane' -o name | sort | head -1 | cut -d/ -f2)" systemctl start kubelet
kubectl wait --for=condition=Ready node --all --timeout=180s
```

## Confirm

`python verifiers/verify.py scenarios/kubelet-stopped-129` passes.
