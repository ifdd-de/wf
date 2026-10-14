# ifdd-de/wf

cookiecutter/cruft template for workflow orchestration with
[Kestra](https://kestra.io) (open-source edition, 2.0 LTS) behind the IFDD
proxy (`ifdd-de/proxy`). The generated instance runs Kestra with PostgreSQL,
starts task containers in a Docker-in-Docker daemon (or on the host socket),
runs Jupyter notebooks with papermill in a local runner image, and pushes
flows from Kestra to a Git content repository.

## Generate an instance

```bash
cruft create --no-input --checkout <tag> \
  --config-file cookiecutter_all.yaml \
  --skip .env --skip secrets --skip certs \
  --output-dir ../instances https://github.com/ifdd-de/wf
```

Then copy the internal CA certificates into `certs/` (meta repository:
`.adm_01_create_services.sh` copies `ca.crt` of the proxy) and follow the
instance documentation (`docs/`). The skip list keeps the
generated secrets and the certificates out of every later `cruft update`.

## Variables

| Variable | Default | Meaning |
|---|---|---|
| `ifdd_wf_prj_name`, `ifdd_wf_prj_slug` | `IFDD WF`, derived | name and directory of the instance |
| `ifdd_wf_host` | `wf` | host name Traefik routes (default for `IFDD_WF_HOST`) |
| `ifdd_wf_entrypoint` | `websecure` | Traefik entry point of the routers |
| `ifdd_wf_dev_port` | `8095` | loopback port of the development compose file |
| `ifdd_wf_admin_email` | `admin@example.org` | user name of Kestra's basic authentication (Kestra requires an email address) |
| `ifdd_wf_kestra_image` | `kestra/kestra:v2.0.4` | upstream image (full image, with plugins) |
| `ifdd_wf_postgres_image` | `postgres:18` | database image |
| `ifdd_wf_docker_mode` | `dind` | `dind`: own privileged Docker daemon, socket shared by volume, no TCP; `socket`: host's `/var/run/docker.sock` |
| `ifdd_wf_dind_image` | `docker:29.8.2-dind` | DinD image |
| `ifdd_wf_runner_python_image` | `python:3.13-slim` | base of the papermill runner image |
| `ifdd_wf_docker_volume_enabled` | `y` | lets flows mount volumes into task containers |
| `ifdd_wf_enable_sso` | `y` | forward authentication through oauth2-proxy of `ifdd-de/proxy` |
| `ifdd_wf_sso_group` | `ifdd_wf_admins` | Keycloak group that may pass |
| `ifdd_wf_sso_auth_address` | `http://oauth2-proxy:4180` | oauth2-proxy as seen from Traefik |
| `ifdd_wf_sso_service` | `oauth2-proxy@docker` | Traefik service of oauth2-proxy (login callback) |
| `ifdd_proxy_network` | `proxy-net` | external network of the proxy |
| `ifdd_be_url` | `https://be.example.org` | ifdd-be for flows and notebooks (`ENV_IFDD_BE_URL` in `secrets/kestra.env`) |
| `ifdd_oidc_realm` | `https://keycloak.example.org/realms/ifdd` | realm URL; its token endpoint becomes `ENV_IFDD_OIDC_TOKEN_URL` |
| `ifdd_keycloak_api_client_id` | `ifdd-api-script` | read-only client of flows and notebooks (`ENV_IFDD_API_CLIENT_ID`) |

`hooks/pre_gen_project.py` rejects values that would render but not work.
`hooks/post_gen_project.py` creates `.env` and `secrets/kestra.env` from the
`.dist` files and fills every `<<generate:...>>` placeholder with a random
value of the stated quality; existing files are never overwritten.

## Documentation of the instance (`docs/`)

Every instance carries its operating documentation as Sphinx sources in
MyST Markdown, in English (`docs/en`) and German (`docs/de`), with the same
files, labels and headings in both. The pages follow the work around the
service: `index` (purpose, architecture), `setup`, `build-release`,
`operations`, `security`, `troubleshooting`, `reference`, plus `notebooks`
(papermill, the backend example). cookiecutter fills in the values of the
instance, and the pages show only what the chosen options produce (Docker
mode, login gate). The instance README is only an entry point that links to
them. `.dockerignore` lists only what the images need, so `docs/` stays out
of the build context.

The pages have no `conf.py` of their own: they are meant to be copied into a
Sphinx project that documents all services. That project needs `myst_parser`
and `sphinxcontrib.mermaid`. Labels start with `ifdd-wf-`; references to
`ifdd-instances-wf` (the instance chapter of the meta repository) resolve
only there.

Rules for editing the pages in the template:

- change both languages in the same commit, and keep headings inside a
  Jinja condition in the same condition in both languages;
- Kestra expressions (`{{ envs.x }}`) are Jinja syntax for cookiecutter:
  wrap them in `{% raw %}`;
- the placeholder check of the CI greps the rendered instance for the text
  `cookiecutter` followed by a dot; do not write it literally.

`tests/check_docs.py` checks a rendered instance: same files, labels and
headings per level in both languages, every label with the prefix, every
reference to an own label resolvable, and a Sphinx build of each language
with `-W` (configuration `tests/docs/conf.py`, versions
`tests/docs/requirements.txt`).

## Requirements on the proxy

With `ifdd_wf_enable_sso=y` the proxy instance needs
`ifdd_proxy_enable_oauth2_proxy=y` (added to `ifdd-de/proxy` together with
this template) and a Keycloak client; see the proxy README, "oauth2-proxy".

## CI

- `template-test.yml`: renders every fixture in `tests/fixtures/`, checks
  for leftover placeholders, runs the instance's static tests, checks and
  builds the documentation (`tests/check_docs.py`) and validates both
  compose files.
- `template-update-test.yml`: generates from the most recent tag and applies
  the current state with `cruft update`.

Not in CI (yet): building the images and starting the stack. See "Honesty
notes".

## Security notes

- **No path prefix: Kestra always runs at the root of its own host name.**
  Up to 26.10.1 the template offered `ifdd_wf_path` (Kestra context path);
  with Kestra 2.0.4 it never worked:
  - the authentication filter only treats requests whose raw path starts with
    `/api/v1` as API requests, so under `<path>/api/v1/...` the API answered
    without basic authentication (observed while building 26.10.1: 401
    without context path, 200 with `/wf`);
  - the UI calls the API without the prefix (`/api/v1/...`), which no router
    matches, so the login fails (observed on 2026-10-05: 404 for
    `https://wf/api/v1/configs`, 200 for `https://wf/wf/api/v1/configs`).
  The variable is gone; an instance with a path needs an own host name.
- Docker access is root-equivalent: on the host with `socket`, inside the
  privileged DinD container with `dind`. Kestra itself runs as root.
- The management port 8081 (health, metrics, unauthenticated) is never
  published.

## Honesty notes

Documentation `docs/` (2026-10-13): rendered with cookiecutter 2.7.1 for
both fixtures and with the `cookiecutter_all.yaml` of the meta repository;
`tests/check_docs.py` passes for each (Sphinx 9.1.0, myst-parser 5.1.0,
sphinxcontrib-mermaid 2.1.1, Python 3.13), the placeholder check finds
nothing and the instance tests pass. The workflow file passes actionlint
1.7.12; the workflow itself has not run. Content: taken from the previous
instance README, this README, the compose files, `dotenv.dist`,
`secrets/kestra.env.dist` and the scripts. Also checked (2026-10-13): one
Sphinx project per language with the pages of all ten service templates (rendered
with `cookiecutter_all.yaml`), the instance chapter of the meta repository
and ifdd-be-core with its OpenAPI document builds with `-W` and no
suppressed warnings, so every cross reference resolves; the Mermaid diagrams
of all services, and of the option variants of the fixtures, render in
headless Chromium 141.0.7390.37 (Playwright 1.56.0, Mermaid 11.12.1 served
locally).

Backend example (2026-10-09), see the instance README: notebook against a
real ifdd-be and Keycloak 26.8.0; both example flows validated by Kestra
2.0.4 (Java 25, plugin-script-python 1.14.0); the new flow ran in Kestra with
the Process runner instead of Docker. The new instance tests fail against the
previous template. Not verified: Docker task runner, `networkMode`, name
resolution inside DinD.

Verified while building 26.10.1 (no Docker available in the build
environment):

- Kestra 2.0.4 (release binary, Java 25, PostgreSQL 16) with the rendered
  `kestra/application.yml`: `${...}` resolution, basic authentication, the
  context-path finding above (API part), `SECRET_*`/`ENV_*` in flows, both example flows
  validated, `system_git_sync.yml` pushed a flow to a local Git repository.
- oauth2-proxy 7.15.5 with the environment of the rendered proxy compose
  file, Traefik 3.7.13 with routers equal to this template's labels and a
  simulated Keycloak: browser redirected to the realm, PKCE, callback on
  `/oauth2/callback`, group member let through, non-member 403.
- The example notebook with the pinned papermill stack (Python 3.12).

Not verified: the three Dockerfiles (no Docker); in particular whether the
Kestra 2.0.4 image has pip in `/app/.venv` (the Dockerfile falls back to uv
and ensurepip and fails loudly otherwise), DinD and the image load into it,
name resolution from task containers inside DinD, and the Python version of
the Kestra image.

Healthcheck of `kestra` and removal of the path (2026-10-05): the endpoint
`/health` on the management port 8081 comes from Kestra's default
configuration (`cli/src/main/resources/application.yml`, tag `v2.0.4`); in a
running instance `curl` exists in the image (neither `wget` nor `bash`) and
`http://localhost:8081/health` answered 200 (checked by the maintainer). The
login failure under a path was observed in a running instance. Rendering with
cookiecutter 2.7.1, the instance tests (the new ones fail against the previous
template) and `docker compose config` (Compose v5.5.1) were run; the
healthcheck itself was not run in Docker.
