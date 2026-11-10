(ifdd-wf-index)=
# {{ cookiecutter.ifdd_wf_prj_name }} (wf)
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

The workflow service of an IFDD node: Kestra (open-source edition) with
PostgreSQL runs flows, starts task containers, runs Jupyter notebooks with
papermill and keeps its flows in a Git content repository. This chapter
describes the instance `{{ cookiecutter.ifdd_wf_prj_slug }}`, generated from
the template `ifdd-de/wf`, from the point of view of the people who set it
up, build, run and secure it.

| | |
|---|---|
| URL | `https://{{ cookiecutter.ifdd_wf_host }}/` (default of `IFDD_WF_HOST`; routed by the proxy, always at the root of its own host) |
| Kestra | `{{ cookiecutter.ifdd_wf_kestra_image }}`, database `{{ cookiecutter.ifdd_wf_postgres_image }}` |
| Task containers | {% if dind %}in an own Docker-in-Docker daemon (`{{ cookiecutter.ifdd_wf_dind_image }}`){% else %}on the host's Docker daemon (socket mounted){% endif %} |
| Access | {% if sso %}login gate of the proxy (Keycloak group `{{ cookiecutter.ifdd_wf_sso_group }}`), then Kestra's own login{% else %}Kestra's own login only{% endif %} |
| Backend for flows | `{{ cookiecutter.ifdd_be_url }}`, client `{{ cookiecutter.ifdd_keycloak_api_client_id }}` (read only) |
| Development | `http://127.0.0.1:{{ cookiecutter.ifdd_wf_dev_port }}/` |
| Content repository | `{{ cookiecutter.ifdd_wf_git_url }}`, branch `{{ cookiecutter.ifdd_wf_git_branch }}`, root namespaces `{{ cookiecutter.ifdd_wf_git_namespaces }}` (production) |

## What the instance contains

Two compose files; the Kestra image (`kestra/`: `Dockerfile`,
`requirements.txt` for Process tasks, `application.yml`){% if dind %}, the
Docker-in-Docker image (`dind/`){% endif %} and the papermill runner image
(`runners/papermill/`), all built locally and with the CA certificates of
`certs/` in their trust store; `.env` and `secrets/kestra.env` with generated
values; the flows of the Git synchronisation (`flows/system/`) and their
helper `kestra/git_sync.py`; example flows and notebooks; the scripts
`adm_01_build.sh`, `adm_02_run.sh`, `adm_03_git_push.sh` and
`adm_99_destroy.sh`.

## Architecture

```{mermaid}
flowchart LR
{%- if sso %}
  Browser -->|HTTPS| Proxy[proxy: Traefik] -->|forwardAuth| OAuth2[oauth2-proxy]
{%- else %}
  Browser -->|HTTPS| Proxy[proxy: Traefik]
{%- endif %}
  Proxy --> Kestra[kestra]
  Kestra -->|db network| PG[(PostgreSQL)]
{%- if dind %}
  Kestra -->|socket volume| DinD[dind: Docker daemon]
  DinD --> Tasks[task containers]
{%- else %}
  Kestra -->|host socket| Docker[host Docker] --> Tasks[task containers]
{%- endif %}
  Tasks -->|"via proxy: be, Keycloak"| Proxy
  Kestra -->|push, hourly| Git[content repository]
  Git -->|restore at start| Kestra
```

| Who | Uses wf for |
|---|---|
| people in the group `{{ cookiecutter.ifdd_wf_sso_group }}` | editing and running flows in the Kestra UI |
| flows and notebooks | reading the backend with the client `{{ cookiecutter.ifdd_keycloak_api_client_id }}` |

## Chapters

```{toctree}
:maxdepth: 2

setup
build-release
operations
security
troubleshooting
reference
notebooks
```

The values of the variables of this instance and how they relate to the
other services are listed in the chapter on the service instances
({ref}`ifdd-instances-wf`).
