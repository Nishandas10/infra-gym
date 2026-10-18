#!/usr/bin/env bash
# Creates the AI agent's Kubernetes identity and a fresh container it runs commands in.
#
# The agent may operate the shop (namespace $APP_NS, set by agent_bench.py from worlds/*.yaml),
# cluster add-ons (kube-system), nodes, the app namespace's labels and admission webhooks: everything the scenarios
# need. It gets NO access to gym-system (the verifier's probe pods) or chaos-mesh, and
# the container cannot see this repo, so it cannot read reference solutions or checks.
set -euo pipefail
# The kind cluster behind the current context (KUBECONFIG=~/.kube/gym/<cluster>), so the agent's kubeconfig
# points at the same cluster its token was created on.
CTX=$(kubectl config current-context)
CLUSTER="${CLUSTER:-${CTX#kind-}}"
# The sandbox container and its kubeconfig. agent_bench.py passes SANDBOX=agent-box-<cluster>, so each cluster has its
# own and oracles or runs on different clusters can go in parallel; without it, the single shared agent-box.
SANDBOX="${SANDBOX:-agent-box}"
if [ "$SANDBOX" = agent-box ]; then KDIR="$HOME/.agent-kube"; else KDIR="$HOME/.agent-kube-$SANDBOX"; fi
APP_NS="${APP_NS:-default}"
mkdir -p "$KDIR"

kubectl delete clusterrolebinding agent-view --ignore-not-found >/dev/null   # from an older guide
# A binding's roleRef cannot change, so one left by an older version of this script that points at another role is
# deleted first and recreated below (kube-system's used to name the namespaced role).
rebind() {  # namespace, binding, role it must point at
  local cur
  cur=$(kubectl -n "$1" get rolebinding "$2" -o jsonpath='{.roleRef.name}' 2>/dev/null || true)
  if [ -n "$cur" ] && [ "$cur" != "$3" ]; then kubectl -n "$1" delete rolebinding "$2" >/dev/null; fi
}
rebind "$APP_NS" gym-agent gym-agent-namespaced
rebind kube-system gym-agent gym-agent-kube-system
kubectl apply -f - >/dev/null << YAML
apiVersion: v1
kind: ServiceAccount
metadata: {name: agent, namespace: ${APP_NS}}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata: {name: gym-agent-namespaced}
rules:
  # Core resources are listed one by one: a "*" here would include "namespaces", and a
  # RoleBinding in a namespace then allows deleting that namespace itself.
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/exec", "pods/attach", "pods/portforward", "pods/eviction",
                "pods/ephemeralcontainers", "services", "services/proxy", "endpoints", "configmaps",
                "secrets", "serviceaccounts", "persistentvolumeclaims", "events", "resourcequotas",
                "limitranges", "replicationcontrollers"]
    verbs: ["*"]
  - apiGroups: ["apps", "batch", "networking.k8s.io", "policy", "autoscaling", "discovery.k8s.io", "events.k8s.io"]
    resources: ["*"]
    verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata: {name: gym-agent-kube-system}
rules:
  # As gym-agent-namespaced, minus exec, attach, port-forward and debug containers: kube-system runs privileged
  # host-network pods (kube-proxy, kindnet), and a shell in one of them is a shell on the node. No fix needs them.
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/eviction", "services", "endpoints", "configmaps", "secrets",
                "serviceaccounts", "persistentvolumeclaims", "events", "resourcequotas", "limitranges",
                "replicationcontrollers"]
    verbs: ["*"]
  - apiGroups: ["apps", "batch", "networking.k8s.io", "policy", "autoscaling", "discovery.k8s.io", "events.k8s.io"]
    resources: ["*"]
    verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata: {name: gym-agent-cluster}
rules:
  - apiGroups: [""]
    resources: ["nodes", "namespaces"]
    verbs: ["get", "list", "watch", "patch", "update"]
  - apiGroups: ["admissionregistration.k8s.io"]
    resources: ["validatingwebhookconfigurations", "mutatingwebhookconfigurations"]
    verbs: ["get", "list", "watch", "patch", "update", "delete"]
  - apiGroups: ["storage.k8s.io", "scheduling.k8s.io", "node.k8s.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: gym-agent, namespace: ${APP_NS}}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: gym-agent-namespaced}
subjects: [{kind: ServiceAccount, name: agent, namespace: ${APP_NS}}]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: gym-agent, namespace: kube-system}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: gym-agent-kube-system}
subjects: [{kind: ServiceAccount, name: agent, namespace: ${APP_NS}}]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata: {name: gym-agent-cluster}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: gym-agent-cluster}
subjects: [{kind: ServiceAccount, name: agent, namespace: ${APP_NS}}]
YAML

# No pod in the app namespace may run on the control-plane node: not pinned there by nodeName, and (when the
# scheduler places it) not with a toleration for the control-plane taint, a wildcard one included. A pod pinned
# to a worker may tolerate anything (host access is refused separately, below). The agent cannot change
# admission policies (the RBAC above only covers webhook configurations), and the namespace is matched by its
# name label, which the API server sets and nobody can change.
CP_NODES=$(kubectl get nodes -l node-role.kubernetes.io/control-plane \
  -o jsonpath="{range .items[*]}'{.metadata.name}',{end}")
CP_NODES="[${CP_NODES%,}]"
kubectl apply -f - >/dev/null << YAML
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: {name: gym-no-control-plane}
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: >-
        !has(object.spec.nodeName) || !(object.spec.nodeName in ${CP_NODES})
      message: pods in ${APP_NS} may not run on the control-plane node
    - expression: >-
        (has(object.spec.nodeName) && object.spec.nodeName != '') || !has(object.spec.tolerations) ||
        !object.spec.tolerations.exists(t,
          (has(t.key) && t.key == 'node-role.kubernetes.io/control-plane') ||
          ((!has(t.key) || t.key == '') && has(t.operator) && t.operator == 'Exists'))
      message: pods in ${APP_NS} may not tolerate the control-plane taint
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata: {name: gym-no-control-plane}
spec:
  policyName: gym-no-control-plane
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: ${APP_NS}}
YAML

# The agent may not give a pod host access (privileged or SYS_ADMIN-like capabilities, host network/PID/IPC,
# hostPath): from such a pod it could reach the node container and, through it, the machine running the benchmark
# (its API keys, the answer keys). Pods made from a workload are created by a controller, so workload templates are
# checked as the agent writes them. A workload that already has host access (kube-proxy, kindnet, the collector
# agent) may still be patched (scheduling, resources, config) as long as the change adds none and leaves every
# container's image, command and args as they were; a debug container may not join a pod that has host access.
# Only the agent is matched: the gym's own injections run with the admin credentials. (The collector agent mounts the
# node's / read-only at /hostfs, and the agent may exec into it; its image has no shell or file tools.)
PRIV="has(c.securityContext) && ((has(c.securityContext.privileged) && c.securityContext.privileged) || (has(c.securityContext.capabilities) && has(c.securityContext.capabilities.add) && c.securityContext.capabilities.add.exists(a, a in ['SYS_ADMIN', 'ALL', 'SYS_PTRACE', 'SYS_MODULE'])))"
SAME="o.name == c.name && o.image == c.image && (has(o.command) ? has(c.command) && o.command == c.command : !has(c.command)) && (has(o.args) ? has(c.args) && o.args == c.args : !has(c.args))"
host_access_policy() {   # <policy name> <resourceRules YAML> <path to the pod spec under the object>
  local name=$1 rules=$2 path=$3
  kubectl apply -f - >/dev/null << YAML
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: {name: ${name}}
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
${rules}
  matchConditions:
    - name: the-agent
      expression: request.userInfo.username == 'system:serviceaccount:${APP_NS}:agent'
  variables:
    - name: new
      expression: object.${path}
    - name: old
      expression: "oldObject == null ? null : oldObject.${path}"
    - name: newPriv
      expression: >-
        (has(variables.new.containers) && variables.new.containers.exists(c, ${PRIV})) ||
        (has(variables.new.initContainers) && variables.new.initContainers.exists(c, ${PRIV})) ||
        (has(variables.new.ephemeralContainers) && variables.new.ephemeralContainers.exists(c, ${PRIV}))
    - name: oldPriv
      expression: >-
        variables.old != null && (
        (has(variables.old.containers) && variables.old.containers.exists(c, ${PRIV})) ||
        (has(variables.old.initContainers) && variables.old.initContainers.exists(c, ${PRIV})) ||
        (has(variables.old.ephemeralContainers) && variables.old.ephemeralContainers.exists(c, ${PRIV})))
    - name: newNS
      expression: >-
        (has(variables.new.hostNetwork) && variables.new.hostNetwork) ||
        (has(variables.new.hostPID) && variables.new.hostPID) || (has(variables.new.hostIPC) && variables.new.hostIPC)
    - name: oldNS
      expression: >-
        variables.old != null && ((has(variables.old.hostNetwork) && variables.old.hostNetwork) ||
        (has(variables.old.hostPID) && variables.old.hostPID) || (has(variables.old.hostIPC) && variables.old.hostIPC))
    - name: newPaths
      expression: >-
        has(variables.new.volumes) ? variables.new.volumes.filter(v, has(v.hostPath)).map(v, v.hostPath.path) : []
    - name: oldPaths
      expression: >-
        variables.old != null && has(variables.old.volumes) ?
        variables.old.volumes.filter(v, has(v.hostPath)).map(v, v.hostPath.path) : []
    - name: sameCode
      expression: >-
        variables.old != null &&
        (!has(variables.new.containers) || variables.new.containers.all(c, has(variables.old.containers) &&
          variables.old.containers.exists(o, ${SAME}))) &&
        (!has(variables.new.initContainers) || variables.new.initContainers.all(c, has(variables.old.initContainers) &&
          variables.old.initContainers.exists(o, ${SAME})))
  validations:
    - expression: >-
        !(variables.newPriv || variables.newNS || size(variables.newPaths) > 0) ||
        (request.operation == 'UPDATE' &&
         (!has(request.subResource) || request.subResource != 'ephemeralcontainers') &&
         (!variables.newPriv || variables.oldPriv) && (!variables.newNS || variables.oldNS) &&
         variables.newPaths.all(p, p in variables.oldPaths) && variables.sameCode)
      message: >-
        the agent may not give a pod host access (privileged, host network/PID/IPC, hostPath, SYS_ADMIN), add any to a
        workload, change the code of a workload that has it, or attach a debug container to a pod that has it
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata: {name: ${name}}
spec:
  policyName: ${name}
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchExpressions:
        - {key: kubernetes.io/metadata.name, operator: In, values: [${APP_NS}, kube-system]}
YAML
}
host_access_policy gym-agent-host-pods '      - {apiGroups: [""], apiVersions: ["v1"], operations: ["CREATE", "UPDATE"], resources: ["pods", "pods/ephemeralcontainers"]}' spec
host_access_policy gym-agent-host-workloads '      - {apiGroups: ["apps"], apiVersions: ["v1"], operations: ["CREATE", "UPDATE"], resources: ["deployments", "daemonsets", "statefulsets", "replicasets"]}
      - {apiGroups: ["batch"], apiVersions: ["v1"], operations: ["CREATE", "UPDATE"], resources: ["jobs"]}
      - {apiGroups: [""], apiVersions: ["v1"], operations: ["CREATE", "UPDATE"], resources: ["replicationcontrollers"]}' spec.template.spec
host_access_policy gym-agent-host-cronjobs '      - {apiGroups: ["batch"], apiVersions: ["v1"], operations: ["CREATE", "UPDATE"], resources: ["cronjobs"]}' spec.jobTemplate.spec.template.spec

TOKEN=$(kubectl create token agent -n "$APP_NS" --duration=24h)
TMP="$KDIR/admin-internal"
kind get kubeconfig --internal --name "$CLUSTER" > "$TMP"
SERVER=$(kubectl --kubeconfig "$TMP" config view --raw -o jsonpath='{.clusters[0].cluster.server}')
CA=$(kubectl --kubeconfig "$TMP" config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
rm -f "$TMP"

CFG="$KDIR/config"
rm -f "$CFG"
kubectl config --kubeconfig "$CFG" set-cluster gym --server="$SERVER" >/dev/null
kubectl config --kubeconfig "$CFG" set clusters.gym.certificate-authority-data "$CA" >/dev/null
kubectl config --kubeconfig "$CFG" set-credentials agent --token="$TOKEN" >/dev/null
kubectl config --kubeconfig "$CFG" set-context agent --cluster=gym --user=agent --namespace="$APP_NS" >/dev/null
kubectl config --kubeconfig "$CFG" use-context agent >/dev/null
chmod 600 "$CFG"

docker rm -f "$SANDBOX" >/dev/null 2>&1 || true
docker run -d --name "$SANDBOX" --network kind \
  -v /usr/local/bin/kubectl:/usr/local/bin/kubectl:ro \
  -v "$KDIR":/kube:ro -e KUBECONFIG=/kube/config \
  ubuntu:24.04 sleep infinity >/dev/null

# No internet or cloud metadata from the sandbox (bench/sandbox_firewall.sh, needs root). Without passwordless sudo
# the run goes on and `agent_bench.py preflight` reports the sandbox as open.
sudo -n bash "$(dirname "$0")/sandbox_firewall.sh" >/dev/null 2>&1 ||
  echo "WARNING: sandbox_firewall.sh could not run (sudo -n): the agent's sandbox can reach the internet" >&2
