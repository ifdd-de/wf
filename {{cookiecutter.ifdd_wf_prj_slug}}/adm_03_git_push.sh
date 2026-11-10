#!/usr/bin/env bash
# Push the flows and namespace files to the content repository now and wait
# for the result (flow system.git_push, which otherwise runs hourly).
# Production only, like the Git synchronisation itself.
# Usage: ./adm_03_git_push.sh
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE=(docker compose -f docker-compose-production.yml)
fail() { echo "ERROR: $*" >&2; exit 1; }

[ $# -eq 0 ] || { echo "usage: $0" >&2; exit 2; }
"${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -qx kestra \
    || fail "Kestra (production) is not running - start it with ./adm_02_run.sh production"
"${COMPOSE[@]}" exec -T kestra python3 /etc/kestra/git_sync.py push
