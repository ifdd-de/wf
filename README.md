# ifdd-de/wf

cookiecutter/cruft template for workflow orchestration with
[Kestra](https://kestra.io) (open-source edition, 2.0 LTS) behind the IFDD
proxy (`ifdd-de/proxy`). The generated instance runs Kestra with PostgreSQL,
starts task containers in a Docker-in-Docker daemon (or on the host socket),
runs Jupyter notebooks with papermill in a local runner image, and keeps
its flows in a Git content repository: pushed hourly, restored into a newly
built instance.

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
| `ifdd_wf_kestra_image` | `kestra/kestra:v2.0.8` | upstream image (full image, with all plugins; the image built from it was 9.2 GB on disk, see "Disk space") |
| `ifdd_wf_postgres_image` | `postgres:18` | database image |
| `ifdd_wf_docker_mode` | `dind` | `dind`: own privileged Docker daemon, socket shared by volume, no TCP; `socket`: host's `/var/run/docker.sock` |
| `ifdd_wf_dind_image` | `docker:29.9.2-dind` | DinD image |
| `ifdd_wf_runner_python_image` | `python:3.14-slim` | base of the papermill runner image |
| `ifdd_wf_docker_volume_enabled` | `y` | lets flows mount volumes into task containers |
| `ifdd_wf_enable_sso` | `y` | forward authentication through oauth2-proxy of `ifdd-de/proxy` |
| `ifdd_wf_sso_group` | `ifdd_wf_admins` | Keycloak group that may pass |
| `ifdd_wf_sso_auth_address` | `http://oauth2-proxy:4180` | oauth2-proxy as seen from Traefik |
| `ifdd_proxy_oauth2_proxy_service` | `ifdd_proxy-oauth2-proxy` | **shared** with `ifdd-de/proxy`: its Traefik service of oauth2-proxy, without `@docker`; the router of the login callback names `<value>@docker`. The default is the name of a proxy with the default project name |
| `ifdd_wf_sso_service` | `oauth2-proxy@docker` | deprecated: a value other than this default still names the service of the login callback (the pre-generation hook warns); leave the default and set `ifdd_proxy_oauth2_proxy_service` |
| `ifdd_wf_git_url` | `https://git.example.org/example/wf-content.git` | content repository of the flows (HTTPS, no credentials; the token goes into `secrets/kestra.env`). The host needs a name with a dot: Kestra's Git client (Java) sends no server name for short names, and the proxy refuses those handshakes in production |
| `ifdd_wf_git_username` | `git` | user name sent with the token |
| `ifdd_wf_git_branch` | `main` | branch of this instance, for example one per stage; must exist |
| `ifdd_wf_git_namespaces` | `ifdd` | root namespaces to synchronise, comma-separated, each with its child namespaces |
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
and `sphinxcontrib.plantuml` (PlantUML with Java and Graphviz).
Labels start with `ifdd-wf-`; references to
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

The check runs PlantUML, so it needs Java and Graphviz.
`tests/docs/get_plantuml.sh` downloads the pinned PlantUML jar into the user
cache, checks its SHA-256 and prints its path:

```bash
export IFDD_PLANTUML_JAR="$(tests/docs/get_plantuml.sh)"
```

## Disk space

The Kestra image of an instance is large: built from `kestra/kestra:v2.0.8`
with the Python packages of `kestra/requirements.txt`, it took 9.17 GB on
disk (integration run of `ifdd-de/meta` on a GitHub runner, 2026-11-18); the
build cache adds several GB until `docker builder prune`. Kestra also
publishes slim images without plugins (`kestra/kestra:v<version>-slim`); the
template does not use them, because flows need at least the Git and script
plugins and own flows may need more.

## Requirements on the proxy

With `ifdd_wf_enable_sso=y` the proxy instance needs
`ifdd_proxy_enable_oauth2_proxy=y` (added to `ifdd-de/proxy` together with
this template) and a Keycloak client; see the proxy README, "oauth2-proxy".

## CI

- `template-test.yml`: renders every fixture in `tests/fixtures/`, checks
  for leftover placeholders, runs the instance's static tests, checks and
  builds the documentation (`tests/check_docs.py`), checks that the router
  of the login callback names the service of the proxy
  (`tests/check_sso_service.py`) and validates both compose files.
- `template-update-test.yml`: generates from the most recent tag and applies
  the current state with `cruft update`.

Not in CI (yet): building the images and starting the stack.

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

## AI assistance

Some parts of this repository, in particular the tests, the test data and the
documentation, were developed or improved with the help of large language
models (LLMs). All changes were reviewed and released by the maintainer.
