#!/usr/bin/env bash
# Pre-flight checks, then start the stack.
# Usage: ./adm_02_run.sh production|development
set -euo pipefail
cd "$(dirname "$0")"

MODE=${1:-}
case "$MODE" in production|development) ;; *) echo "usage: $0 production|development" >&2; exit 2;; esac
COMPOSE=(docker compose -f "docker-compose-$MODE.yml")
fail() { echo "ERROR: $*" >&2; exit 1; }

[ -f .env ] || fail ".env missing"
[ -f secrets/kestra.env ] || fail "secrets/kestra.env missing"
grep -v '^ *#' .env secrets/kestra.env | grep -q '<<generate:' && fail "placeholders <<generate:...>> left in .env or secrets/kestra.env"

set -a; . ./.env; set +a
[ -n "${IFDD_WF_RUNNER_PAPERMILL_IMAGE:-}" ] || fail "IFDD_WF_RUNNER_PAPERMILL_IMAGE not set"

if [ "$MODE" = production ]; then
    docker network inspect "{{ cookiecutter.ifdd_proxy_network }}" >/dev/null 2>&1 \
        || fail "Docker network {{ cookiecutter.ifdd_proxy_network }} missing - start the proxy (ifdd-de/proxy) first"
fi

docker image inspect "$IFDD_WF_RUNNER_PAPERMILL_IMAGE" >/dev/null 2>&1 \
    || fail "runner image $IFDD_WF_RUNNER_PAPERMILL_IMAGE missing - run ./adm_01_build.sh $MODE"
{%- if cookiecutter.ifdd_wf_docker_mode == "dind" %}

# The runner images are local; the DinD daemon has its own image store and
# cannot pull them. Load them into it (cheap when unchanged).
"${COMPOSE[@]}" up -d --wait dind
echo "Loading $IFDD_WF_RUNNER_PAPERMILL_IMAGE into the Docker-in-Docker daemon"
docker save "$IFDD_WF_RUNNER_PAPERMILL_IMAGE" | "${COMPOSE[@]}" exec -T dind docker load
{%- endif %}

"${COMPOSE[@]}" up -d

if [ "$MODE" = production ]; then
    echo "Kestra: https://${IFDD_WF_HOST}/"
else
    echo "Kestra: http://127.0.0.1:${IFDD_WF_DEV_PORT}/  (user ${IFDD_WF_ADMIN_USER}, password in .env)"
fi
