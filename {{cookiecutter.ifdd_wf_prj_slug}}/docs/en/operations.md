(ifdd-wf-operations)=
# Operations
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}

## Start, stop, order

```bash
./adm_02_run.sh production       # checks, {% if dind %}loads the runner images into DinD, {% endif %}docker compose up -d
docker compose -f docker-compose-production.yml ps
docker compose -f docker-compose-production.yml down     # keeps the volumes
```

`adm_02_run.sh` refuses to start without `.env`, without
`secrets/kestra.env`, with `<<generate:...>>` placeholders left, without the
proxy network (production) or without the runner image. Kestra waits for a
healthy database{% if dind %} and a healthy Docker-in-Docker daemon{% endif %}.
On shutdown it waits up to five minutes for running tasks
(`stop_grace_period: 6m`). Start it after the proxy, Keycloak and the
backend (`.adm_03_up_services.sh` of the meta repository does).

## Health checks

| Container | Check | Interval |
|---|---|---|
| `kestra` | `curl` on `http://localhost:8081/health` (management port, not published) | 15 s, timeout 5 s, 5 retries, start period 120 s |
| `postgres` | `pg_isready -d kestra -U kestra` | 10 s, 10 retries |
{%- if dind %}
| `dind` | `docker info` | 10 s, 12 retries |
{%- endif %}

All containers restart with `restart: always`.

## Logs

```bash
docker compose -f docker-compose-production.yml logs -f kestra
```

The logs of flows and tasks are in the Kestra UI (executions).

## Task containers
{%- if dind %}

Containers that flows start run in the `dind` service: a privileged Docker
daemon that listens only on `/dind/docker.sock` in a volume shared with
Kestra. Kestra's Docker task runner uses that socket when
`/var/run/docker.sock` does not exist. The daemon has its own image store:
the local runner images are loaded by `adm_02_run.sh`; everything else is
pulled by the daemon, with the CAs from `certs/`.

In production the `dind` container is also on
`{{ cookiecutter.ifdd_proxy_network }}`. A task with
`networkMode: "{% raw %}{{ envs.task_network }}{% endraw %}"` (`host`, from
`secrets/kestra.env`) shares that network and reaches other services by
their names, through the proxy's network aliases. Without it, task
containers cannot resolve service names.
{%- else %}

Containers that flows start run on the host's Docker daemon
(`/var/run/docker.sock` mounted into Kestra). A task that calls other
services by name sets
`networkMode: "{% raw %}{{ envs.task_network }}{% endraw %}"`
(`{{ cookiecutter.ifdd_proxy_network }}`, from `secrets/kestra.env`).
{%- endif %}

Flows mount volumes into task containers only if
`ifdd_wf_docker_volume_enabled=y` (here
`{{ cookiecutter.ifdd_wf_docker_volume_enabled }}`); the paths then refer to
{% if dind %}the Docker-in-Docker container{% else %}the host{% endif %}.

```{note}
Not tested: the Docker task runner, `networkMode` and name resolution from
task containers{% if dind %} inside the Docker-in-Docker daemon{% endif %}.
```

## Git synchronisation

`examples/flows/system_git_sync.yml` (namespace `system`, hourly) pushes the
flows and namespace files of the listed namespaces with
`io.kestra.plugin.git.NamespaceSync`, `sourceOfTruth: KESTRA`. Edits in Git
are not pulled back. `whenMissingInSource: KEEP` leaves flows deleted in
Kestra in Git; switch to `DELETE` to mirror deletions.

## Applying changes

| Changed | To do |
|---|---|
| `secrets/kestra.env` | `./adm_02_run.sh production` (Kestra reads it at start) |
| `kestra/application.yml` | restart Kestra |
| `certs/`, `kestra/Dockerfile`, `kestra/requirements.txt`, {% if dind %}`dind/`, {% endif %}`runners/`, image versions | `./adm_01_build.sh production`, then `./adm_02_run.sh production` |

## Backup

Back up `.env`, `secrets/kestra.env` and the volumes `postgres-data` and
`kestra-storage` together. Without `IFDD_WF_ENCRYPTION_KEY` the encrypted
values in the database cannot be read. The flows are also in the content
repository (Git synchronisation).

```{note}
Not tested: backup and restore.
```

## Updates

Template updates arrive with `cruft update --skip .env --skip secrets --skip
certs`. `secrets/kestra.env` is written only once: entries that a new
template version adds to `kestra.env.dist` (for example `ENV_TASK_NETWORK`)
have to be added by hand. Changing `IFDD_WF_DB_PASSWORD` in `.env` alone
locks Kestra out: PostgreSQL keeps the password it was created with.
