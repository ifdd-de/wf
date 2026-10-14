(ifdd-wf-setup)=
# Setup
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

## Prerequisites

| What | Why |
|---|---|
| Docker with Compose | Kestra, PostgreSQL{% if dind %}, the Docker-in-Docker daemon{% endif %} and the runners run as containers; the images are built locally |
| the external network `{{ cookiecutter.ifdd_proxy_network }}` and a running proxy instance | Traefik routes `IFDD_WF_HOST` to Kestra; task containers reach the other services through it |
{%- if sso %}
| the login gate of the proxy (`ifdd_proxy_enable_oauth2_proxy=y`) with the redirect URI `https://<IFDD_WF_HOST>/oauth2/callback` in its client | every request passes oauth2-proxy |
| the Keycloak group `{{ cookiecutter.ifdd_wf_sso_group }}` | its members may pass the gate |
{%- endif %}
| the CA certificate of the proxy, if it uses a CA of its own | it is built into the images |
| a Git content repository and a token with write access to it only | the flows are pushed there |

## Create the instance

Usually the meta repository creates every instance in one go
(`.adm_meta_01_all.sh`, step `.adm_01_create_services.sh`): it runs
`cruft create` with the shared variable file `.cookiecutter_all.yaml`,
copies `certs/ca.crt` of the proxy into `certs/` and the secret of the
client `{{ cookiecutter.ifdd_keycloak_api_client_id }}` into
`secrets/kestra.env`. By hand, from the directory that holds the instances,
with the skip list this template recommends:

```bash
cruft create --no-input --config-file .cookiecutter_all.yaml \
  --skip .env --skip secrets --skip certs \
  https://github.com/ifdd-de/wf
cp proxy/certs/ca.crt {{ cookiecutter.ifdd_wf_prj_slug }}/certs/
```

The meta repository passes `--skip envs --skip .env`.

## Configuration and secrets

The post-generation hook creates `.env` and `secrets/kestra.env` from their
`.dist` files and fills every `<<generate:...>>` placeholder with a random
value; existing files are never overwritten.

| File | Holds |
|---|---|
| `.env` | host, development port, Kestra's login (`IFDD_WF_ADMIN_USER`, `IFDD_WF_ADMIN_PASSWORD`), database password, encryption key, the tag of the runner image |
| `secrets/kestra.env` | flow secrets `SECRET_<NAME>` (base64) and flow variables `ENV_<NAME>` (plain), handed to Kestra |

Fill in `secrets/kestra.env` by hand: the Git token (`SECRET_GIT_TOKEN`,
base64), `ENV_GIT_URL`, `ENV_GIT_USERNAME`, `ENV_GIT_BRANCH`, and the secret
of `{{ cookiecutter.ifdd_keycloak_api_client_id }}`
(`SECRET_IFDD_API_CLIENT_SECRET`, base64; the meta repository does that one).
Encode without a trailing newline: `printf '%s' 'value' | base64 -w0`.
The entries are listed in {ref}`ifdd-wf-reference`, the template variables
in {ref}`ifdd-instances-wf`.

## First start

```bash
./adm_01_build.sh production
./adm_02_run.sh production
```

Then open `https://<IFDD_WF_HOST>/` and log in{% if sso %} (Keycloak first,
then{% else %} with{% endif %} `IFDD_WF_ADMIN_USER` and `IFDD_WF_ADMIN_PASSWORD`
from `.env`{% if sso %}){% endif %}. Import
`examples/flows/system_git_sync.yml` after adjusting its namespace list, run
it once and check the content repository.

The database starts empty. Flows of an older instance are imported in the
UI or through the API; Kestra 2.0 changed several task types (for example
`ForEach` -> `Loop`), so check the Kestra migration guide for 2.0.

## Local development

```bash
./adm_01_build.sh development
./adm_02_run.sh development
```

Kestra is then at `http://127.0.0.1:{{ cookiecutter.ifdd_wf_dev_port }}/`
with the credentials from `.env`: no proxy, no login gate, and neither Kestra
nor the task containers are on the proxy network.
