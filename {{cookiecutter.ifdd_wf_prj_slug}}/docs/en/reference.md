(ifdd-wf-reference)=
# Reference
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

The variables of the template and their values in this instance are listed
in {ref}`ifdd-instances-wf`. This page lists what is not a template
variable.

## Layout

| Path | Content |
|---|---|
| `docker-compose-production.yml` | behind the proxy (`{{ cookiecutter.ifdd_proxy_network }}`){% if sso %}, with the login gate (Keycloak group `{{ cookiecutter.ifdd_wf_sso_group }}`){% endif %} |
| `docker-compose-development.yml` | `http://127.0.0.1:{{ cookiecutter.ifdd_wf_dev_port }}/`, no proxy |
| `kestra/` | image (`Dockerfile`, `requirements.txt` for Process tasks) and `application.yml` |
{%- if dind %}
| `dind/` | Docker-in-Docker image for task containers |
{%- endif %}
| `runners/papermill/` | local runner image for notebooks |
| `build/install-certs.sh` | adds `certs/*` to the trust store of every image |
| `certs/` | internal CA certificates (git-ignored) |
| `secrets/kestra.env` | flow secrets and flow variables (git-ignored) |
| `.env` | host, ports, generated passwords and keys (git-ignored) |
| `examples/` | Git sync flow, papermill flow, backend example flow and notebooks |
| `adm_01_build.sh`, `adm_02_run.sh` | build; check and start |

## Environment (`.env`)

| Variable | Default here | Meaning |
|---|---|---|
| `IFDD_WF_HOST` | `{{ cookiecutter.ifdd_wf_host }}` | host the proxy routes to Kestra |
| `IFDD_WF_DEV_PORT` | `{{ cookiecutter.ifdd_wf_dev_port }}` | port on 127.0.0.1 in development |
| `IFDD_WF_ADMIN_USER` | `{{ cookiecutter.ifdd_wf_admin_email }}` | Kestra's login (an e-mail address) |
| `IFDD_WF_ADMIN_PASSWORD` | generated | at least 8 characters with lower case, upper case and digit |
| `IFDD_WF_DB_PASSWORD` | generated | set once |
| `IFDD_WF_ENCRYPTION_KEY` | generated | AES key for secret inputs and outputs |
| `IFDD_WF_RUNNER_PAPERMILL_IMAGE` | `{{ cookiecutter.ifdd_wf_prj_slug }}-papermill:local` | tag of the papermill runner; flows read it as `{% raw %}{{ envs.runner_papermill_image }}{% endraw %}` |

## Flow secrets and variables (`secrets/kestra.env`)

| Entry | Read in flows as | Content |
|---|---|---|
| `SECRET_<NAME>` (base64) | `{% raw %}{{ secret('<NAME>') }}{% endraw %}` | secrets |
| `ENV_<NAME>` (plain) | `{% raw %}{{ envs.<name> }}{% endraw %}` (lower case) | variables |

| Entry | Default here |
|---|---|
| `SECRET_GIT_TOKEN` | empty |
| `ENV_GIT_URL`, `ENV_GIT_USERNAME`, `ENV_GIT_BRANCH` | example values |
| `ENV_IFDD_BE_URL` | `{{ cookiecutter.ifdd_be_url }}` |
| `ENV_IFDD_OIDC_TOKEN_URL` | `{{ cookiecutter.ifdd_oidc_realm }}/protocol/openid-connect/token` |
| `ENV_IFDD_API_CLIENT_ID` | `{{ cookiecutter.ifdd_keycloak_api_client_id }}` |
| `SECRET_IFDD_API_CLIENT_SECRET` | empty |
| `ENV_TASK_NETWORK` | `{% if dind %}host{% else %}{{ cookiecutter.ifdd_proxy_network }}{% endif %}` |

## Containers and networks

| Container | Port | Networks |
|---|---|---|
| `kestra` | 8080 (routed by the proxy; 127.0.0.1:`IFDD_WF_DEV_PORT` in development), 8081 management, not published | default, `db`, `{{ cookiecutter.ifdd_proxy_network }}` |
| `postgres` | 5432 | `db` (internal) |
{%- if dind %}
| `dind` | none (unix socket in the volume `dind-socket`) | default, `{{ cookiecutter.ifdd_proxy_network }}` |
{%- endif %}

Volumes: `postgres-data`, `kestra-storage`, `kestra-wd`{% if dind %},
`dind-socket`, `dind-data`{% endif %}.

Router and service: `{{ cookiecutter.ifdd_wf_prj_slug }}`, rule
`Host(<IFDD_WF_HOST>)`, entry point `{{ cookiecutter.ifdd_wf_entrypoint }}`,
port 8080{% if sso %}; middleware `{{ cookiecutter.ifdd_wf_prj_slug }}-sso`
(forwardAuth to `{{ cookiecutter.ifdd_wf_sso_auth_address }}`), and the
router `{{ cookiecutter.ifdd_wf_prj_slug }}-oauth2` for `/oauth2/` to
`{{ cookiecutter.ifdd_wf_sso_service }}`{% endif %}.
