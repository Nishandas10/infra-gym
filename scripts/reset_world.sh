#!/usr/bin/env bash
set -e

# Pin the chart version so a reset never silently upgrades the app, and apply
# the local overrides (see values-local.yaml for why they exist).
CHART_VERSION="0.42.0"
VALUES_FILE="$(dirname "$0")/values-local.yaml"

echo "Resetting my-shop to its known-good state..."
helm upgrade my-shop open-telemetry/opentelemetry-demo \
  --version "$CHART_VERSION" \
  -f "$VALUES_FILE" \
  --wait --timeout 10m
echo "Reset complete."
