#!/usr/bin/env bash
set -e
echo "Resetting	my-shop	to	its	known-good	state..."
helm upgrade my-shop open-telemetry/opentelemetry-demo --wait --timeout 5m
echo "Reset complete."