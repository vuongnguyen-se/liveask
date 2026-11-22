#!/usr/bin/env bash
# Zero-downtime rolling update (NFR-2): keeps a screen open and questions flowing while
# `kubectl rollout restart deployment/liveask` replaces every pod. Needs the cluster running
# (minikube: kubectl apply -k k8s/overlays/local). On AWS, skip the port-forward and run
#   BASE_URL=http://<alb-address> node e2e/rollout.js
set -euo pipefail

PORT="${PORT:-8088}"
cd "$(dirname "$0")/../e2e"
[ -d node_modules ] || npm install --no-audit --no-fund

kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller "$PORT:80" >/dev/null &
PF=$!
trap 'kill "$PF" 2>/dev/null || true' EXIT
sleep 3

BASE_URL="http://localhost:$PORT" node rollout.js
