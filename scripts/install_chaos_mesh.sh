#!/usr/bin/env bash
# Installs Chaos Mesh (Playbook step 1.17), pinned and trimmed for a 6 GB WSL VM:
#   - containerd runtime settings, as kind uses containerd
#   - one controller replica instead of three
#   - no web dashboard (scenarios are driven from YAML files)
#   - the DNS server that DNSChaos needs (Playbook note before dns-error-005)
set -e

CHAOS_MESH_VERSION="2.8.4"

helm repo add chaos-mesh https://charts.chaos-mesh.org >/dev/null 2>&1 || true
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --version "$CHAOS_MESH_VERSION" \
  --namespace chaos-mesh --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set controllerManager.replicaCount=1 \
  --set dashboard.create=false \
  --set dnsServer.create=true \
  --wait --timeout 10m
kubectl get pods -n chaos-mesh
