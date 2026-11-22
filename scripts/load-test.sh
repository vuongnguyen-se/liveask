#!/usr/bin/env bash
# Generates CPU load inside the cluster so you can watch the HPA add pods:
#   terminal 1: ./scripts/load-test.sh
#   terminal 2: kubectl -n liveask get hpa,pods -w
# Stop with Ctrl+C; the load pod is deleted on exit.
set -euo pipefail

# Git Bash on Windows would rewrite /bin/sh into a Windows path; stop that.
export MSYS_NO_PATHCONV=1

kubectl -n liveask run load-generator --rm -i --tty --restart=Never \
  --image=busybox:1.37 -- \
  sh -c 'while true; do wget -q -O- "http://liveask/burn?ms=300" >/dev/null; done'
