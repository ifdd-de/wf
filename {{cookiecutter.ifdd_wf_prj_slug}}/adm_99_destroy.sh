{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" -%}
#!/usr/bin/env bash
# Delete this instance completely: push the flows to the content repository
# one last time (adm_03_git_push.sh), then remove the containers, all volumes
# (database, Kestra storage{% if dind %}, Docker-in-Docker data{% endif %}) and the locally built
# images, and finally this directory with .env and secrets/.
#
# Executions, logs, the KV store and secrets are lost; flows and namespace
# files come back from Git when the instance is generated again and started
# with ./adm_02_run.sh production.
# Usage: ./adm_99_destroy.sh   (asks for confirmation on a terminal)
set -euo pipefail
cd "$(dirname "$0")"
DIR=$(pwd -P)

fail() { echo "ERROR: $*" >&2; exit 1; }

[ $# -eq 0 ] || { echo "usage: $0" >&2; exit 2; }
[ -t 0 ] || fail "needs a terminal to confirm; nothing changed"
[ -f .env ] || fail ".env missing; nothing changed"
[ -f docker-compose-production.yml ] || fail "not an instance directory: $DIR"
set -a; . ./.env; set +a

echo "This deletes the Kestra instance in $DIR:"
echo "containers, volumes, local images and the directory itself."
printf "Type 'destroy' to continue: "
answer=""
read -r answer || true
[ "$answer" = destroy ] || fail "not confirmed; nothing changed"

./adm_03_git_push.sh || fail "the last push to Git failed; nothing deleted"

for mode in production development; do
    docker compose -f "docker-compose-$mode.yml" down --volumes --remove-orphans \
        || echo "WARNING: docker compose down ($mode) failed" >&2
done

for image in "{{ cookiecutter.ifdd_wf_prj_slug }}-kestra:local"{% if dind %} "{{ cookiecutter.ifdd_wf_prj_slug }}-dind:local"{% endif %} "${IFDD_WF_RUNNER_PAPERMILL_IMAGE:-}"; do
    [ -n "$image" ] || continue
    if docker image inspect "$image" >/dev/null 2>&1; then
        docker image rm "$image" >/dev/null || echo "WARNING: could not remove image $image" >&2
    fi
done

cd ..
rm -rf -- "$DIR"
echo "Deleted $DIR."
echo "Rebuild: cruft create, put the Git token into secrets/kestra.env, ./adm_01_build.sh production, ./adm_02_run.sh production"
