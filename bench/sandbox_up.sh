#!/usr/bin/env bash
# Creates the AI agent's Kubernetes identity and a fresh container it runs commands in.
#
# The agent may operate the shop (namespace $APP_NS, set by agent_bench.py from worlds/*.yaml),
# cluster add-ons (kube-system), nodes, the app namespace's labels and admission webhooks: everything the scenarios
# need. It gets NO access to gym-system (the verifier's probe pods) or chaos-mesh, and
# the container cannot see this repo, so it cannot read reference solutions or checks.
set -euo pipefail
CLUSTER=ai-gym
KDIR="$HOME/.agent-kube"
APP_NS="${APP_NS:-default}"
mkdir -p "$KDIR"

kubectl delete clusterrolebinding agent-view --ignore-not-found >/dev/null   # from an older guide
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
                "limitranges", "replicationcontrollers", "podtemplates"]
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
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: gym-agent-namespaced}
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
# to a worker may tolerate anything, so `kubectl debug node/<worker>` still works. The agent cannot change
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

docker rm -f agent-box >/dev/null 2>&1 || true
docker run -d --name agent-box --network kind \
  -v /usr/local/bin/kubectl:/usr/local/bin/kubectl:ro \
  -v "$KDIR":/kube:ro -e KUBECONFIG=/kube/config \
  ubuntu:24.04 sleep infinity >/dev/null
