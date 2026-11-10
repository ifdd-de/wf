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

In production Kestra keeps the flows and namespace files (for example
notebooks) of the root namespaces `{{ cookiecutter.ifdd_wf_git_namespaces }}` and their child namespaces in the
content repository `{{ cookiecutter.ifdd_wf_git_url }}`, branch `{{ cookiecutter.ifdd_wf_git_branch }}`. Layout in Git:
`<namespace>/flows/<flow>.yaml` and `<namespace>/files/<path>`. The two flows
of the namespace `system` that do the work come from `flows/system/` of the
instance, not from Git; `adm_02_run.sh` loads them on every start, so edits
in the UI do not last.

### Push (Kestra to Git)

`system.git_push` runs hourly; `./adm_03_git_push.sh` runs it at once and
waits for the result. Kestra is the source of truth: a flow or file deleted
in Kestra is deleted in Git as well and stays in its history. Changes made in
Git are overwritten by the next push; they reach Kestra only through a
rebuild. Two pushes never run at the same time.

### Restore (Git to Kestra)

`./adm_02_run.sh production` checks every root namespace after the start. A
root namespace without any flow in Kestra, its child namespaces included, is
restored from Git by `system.git_restore`; the others are left alone. Only
when every restore succeeded is `system.git_push` loaded. Otherwise the
script ends with an error, Kestra keeps running and nothing is pushed, so a
new, empty instance cannot overwrite the repository. The restore lists the
namespace folders in Git and restores each on its own: the open-source
edition cannot create a namespace through its API.

`kestra/git_sync.py` does this inside the Kestra container through Kestra's
API on `localhost`, with Kestra's login from `.env`. The Git tasks call
Kestra's API the same way (`kestra.tasks.sdk.authentication` in
`kestra/application.yml`), not through the public URL behind the proxy.

### Delete and rebuild

```bash
./adm_99_destroy.sh     # asks for "destroy"
```

The script pushes once more and stops if that fails. Then it removes the
containers, all volumes, the locally built images and the instance directory
with `.env` and `secrets/`. To rebuild, generate the instance again
({ref}`ifdd-wf-setup`), enter `SECRET_GIT_TOKEN` and the other secrets in
`secrets/kestra.env`, then `./adm_01_build.sh production` and
`./adm_02_run.sh production`: the flows and namespace files come back from
Git. Executions and their logs, the KV store, secrets outside
`secrets/kestra.env` and flow drafts (they are never pushed) do not come
back.

### Limits

Observed with Kestra 2.0.8 and plugin-git 4.6.3:

- A child namespace that holds namespace files but no flow is not pushed.
  Keep such files in a namespace with a flow, for example the root.
- When the last flow of a child namespace is deleted, the namespace is gone
  from Kestra but its folder stays in Git, and a rebuild brings it back.
  Delete the folder in the repository by hand.
- A rebuild restores the state of the branch; what was not pushed is lost.

```{note}
Not tested: the synchronisation inside the containers of this instance
(images, networks, a TLS-inspecting proxy). It was tested with the Kestra
2.0.8 release binary and plugin-git 4.6.3 against local repositories, one of
them behind HTTPS with an own CA.
```

## Applying changes

| Changed | To do |
|---|---|
| `secrets/kestra.env` | `./adm_02_run.sh production` (Kestra reads it at start) |
| `kestra/application.yml` | restart Kestra |
| `flows/system/`, `kestra/git_sync.py` | `./adm_02_run.sh production` (loads the flows again) |
| `certs/`, `build/`, `kestra/Dockerfile`, `kestra/requirements.txt`, {% if dind %}`dind/`, {% endif %}`runners/`, image versions | `./adm_01_build.sh production`, then `./adm_02_run.sh production` |

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
have to be added by hand. A template variable that a new template
version adds (for example `ifdd_wf_git_url`) gets the template's default in
an existing instance; set it with `cruft update --variables-to-update`.
Changing `IFDD_WF_DB_PASSWORD` in `.env` alone
locks Kestra out: PostgreSQL keeps the password it was created with.
