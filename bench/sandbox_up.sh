#!/usr/bin/env bash
# Creates the AI agent's Kubernetes identity and a fresh container it runs commands in.
#
# The agent may operate the shop (namespace default), cluster add-ons (kube-system),
# nodes, the default namespace's labels and admission webhooks: everything the scenarios
# need. It gets NO access to gym-system (the verifier's probe pods) or chaos-mesh, and
# the container cannot see this repo, so it cannot read reference solutions or checks.
set -euo pipefail
CLUSTER=ai-gym
KDIR="$HOME/.agent-kube"
mkdir -p "$KDIR"

kubectl delete clusterrolebinding agent-view --ignore-not-found >/dev/null   # from an older guide
kubectl apply -f - >/dev/null << 'YAML'
apiVersion: v1
kind: ServiceAccount
metadata: {name: agent, namespace: default}
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
metadata: {name: gym-agent, namespace: default}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: gym-agent-namespaced}
subjects: [{kind: ServiceAccount, name: agent, namespace: default}]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: gym-agent, namespace: kube-system}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: gym-agent-namespaced}
subjects: [{kind: ServiceAccount, name: agent, namespace: default}]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata: {name: gym-agent-cluster}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: gym-agent-cluster}
subjects: [{kind: ServiceAccount, name: agent, namespace: default}]
YAML

TOKEN=$(kubectl create token agent -n default --duration=24h)
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
kubectl config --kubeconfig "$CFG" set-context agent --cluster=gym --user=agent --namespace=default >/dev/null
kubectl config --kubeconfig "$CFG" use-context agent >/dev/null
chmod 600 "$CFG"

docker rm -f agent-box >/dev/null 2>&1 || true
docker run -d --name agent-box --network kind \
  -v /usr/local/bin/kubectl:/usr/local/bin/kubectl:ro \
  -v "$KDIR":/kube:ro -e KUBECONFIG=/kube/config \
  ubuntu:24.04 sleep infinity >/dev/null
