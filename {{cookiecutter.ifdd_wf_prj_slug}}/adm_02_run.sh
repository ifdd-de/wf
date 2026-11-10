#!/usr/bin/env bash
# Pre-flight checks, then start the stack. In production, then load the Git
# synchronisation flows (flows/system/): restore every root namespace that has
# no flow from the content repository, and only if that succeeded load the
# hourly push (kestra/git_sync.py bootstrap).
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
    grep -Eq '^SECRET_GIT_TOKEN=.+' secrets/kestra.env \
        || fail "SECRET_GIT_TOKEN is empty in secrets/kestra.env - enter the token of the content repository, base64: printf '%s' TOKEN | base64 -w0"
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

if [ "$MODE" = production ]; then
    "${COMPOSE[@]}" up -d --wait --wait-timeout 600
    "${COMPOSE[@]}" exec -T kestra python3 /etc/kestra/git_sync.py bootstrap \
        || fail "Git synchronisation not set up; Kestra keeps running without the hourly push (see above)"
    echo "Kestra: https://${IFDD_WF_HOST}/"
else
    "${COMPOSE[@]}" up -d
    echo "Kestra: http://127.0.0.1:${IFDD_WF_DEV_PORT}/  (user ${IFDD_WF_ADMIN_USER}, password in .env)"
fi
