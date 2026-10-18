#!/bin/bash
# Network limits for the agent's sandbox containers (agent-box*), in Docker's DOCKER-USER chain (needs root):
#   - a sandbox reaches only the kind network (its cluster's API server and nodes): no internet, no cloud APIs
#   - nothing on the kind network (nodes, their pods, the sandboxes) reaches the cloud metadata server
#     (169.254.169.254), which hands out the machine's cloud identity
# The model's API calls are made by the harness on the host, not from the sandbox, so they are not affected.
# Idempotent: the rules live in their own chain (GYM-SANDBOX), rebuilt from the running sandboxes on every call
# (a sandbox's address changes when it is recreated). sandbox_up.sh calls it through `sudo -n`; preflight checks it.
# usage: sudo bash bench/sandbox_firewall.sh
set -euo pipefail
SUBNET=$(docker network inspect kind -f '{{range .IPAM.Config}}{{.Subnet}} {{end}}' | tr ' ' '\n' | grep -v ':' | grep . | head -1)
[ -n "$SUBNET" ] || { echo "sandbox_firewall: no IPv4 subnet on the kind network" >&2; exit 1; }
iptables -N GYM-SANDBOX 2>/dev/null || true
iptables -F GYM-SANDBOX
iptables -C DOCKER-USER -j GYM-SANDBOX 2>/dev/null || iptables -I DOCKER-USER 1 -j GYM-SANDBOX
iptables -A GYM-SANDBOX -s "$SUBNET" -d 169.254.169.254/32 -j DROP
n=0
for c in $(docker ps --format '{{.Names}}' | grep '^agent-box' || true); do
  ip=$(docker inspect -f '{{with index .NetworkSettings.Networks "kind"}}{{.IPAddress}}{{end}}' "$c")
  [ -n "$ip" ] || continue
  iptables -A GYM-SANDBOX -s "$ip/32" ! -d "$SUBNET" -j DROP
  n=$((n + 1))
done
echo "sandbox_firewall: $n sandbox(es) limited to $SUBNET; no metadata server from $SUBNET"
