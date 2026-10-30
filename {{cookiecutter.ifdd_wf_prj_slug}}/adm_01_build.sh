#!/usr/bin/env bash
# Build the images of this instance: Kestra{% if cookiecutter.ifdd_wf_docker_mode == "dind" %}, Docker-in-Docker{% endif %} and the runners.
# Usage: ./adm_01_build.sh production|development
#
# Run again after a change to certs/, kestra/, {% if cookiecutter.ifdd_wf_docker_mode == "dind" %}dind/, {% endif %}runners/ or the image
# versions, then ./adm_02_run.sh.
set -euo pipefail
cd "$(dirname "$0")"

MODE=${1:-}
case "$MODE" in production|development) ;; *) echo "usage: $0 production|development" >&2; exit 2;; esac
COMPOSE=(docker compose -f "docker-compose-$MODE.yml")

[ -f .env ] || { echo ".env missing (created at generation from dotenv.dist)" >&2; exit 1; }

certs=$(find certs -maxdepth 1 -type f \( -name '*.crt' -o -name '*.pem' \) | wc -l)
echo "CA certificates in certs/: $certs"

# --pull: fetch the pinned base images again, so security fixes of a moving
# base (e.g. python:3.14-slim) are picked up.
"${COMPOSE[@]}" --profile runners build --pull
