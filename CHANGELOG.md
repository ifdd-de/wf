# Changelog

The version scheme follows the other IFDD templates: `YY.MM.N`.

## [Unreleased]

- The router of the login callback names the Traefik service of oauth2-proxy
  through the new shared variable `ifdd_proxy_oauth2_proxy_service` (default
  `ifdd_proxy-oauth2-proxy`, the name a proxy with the default project name
  declares), plus `@docker`. `ifdd-de/proxy` names its service with the same
  variable. Before, the default `oauth2-proxy@docker` matched no proxy since
  26.10.3; Traefik dropped the router, and every login ended in a loop.
- `ifdd_wf_sso_service` is deprecated: a value other than its default
  `oauth2-proxy@docker` still wins, and the pre-generation hook warns.
- Setup page: section on several servers (login gate of the own server,
  redirect URI in the realm, CA of the other server); troubleshooting: the
  login loop.
- Fixture `multi-server`; `tests/check_sso_service.py` checks the router of
  the login callback for every fixture.
- Upgrade: `cruft update --variables-to-update
  '{"ifdd_proxy_oauth2_proxy_service": "<name in the proxy instance>"}'`
  (and `ifdd_wf_sso_service` back to `oauth2-proxy@docker` if it was set),
  then recreate Kestra (`docker compose -f docker-compose-production.yml up -d`).

## [26.10.3] - 2026-10-30

- Kestra v2.0.8 (`ifdd_wf_kestra_image`, was v2.0.4), Docker-in-Docker
  `docker:29.9.2-dind` (was 29.8.2), papermill runner on `python:3.14-slim`
  (`ifdd_wf_runner_python_image`, was `python:3.13-slim`).
- Python packages of the Kestra and the runner image: pandas 3.1.0 (was
  3.0.6), SQLAlchemy 2.1.6 (was 2.1.4); papermill 2.7.0, ipykernel 7.4.0 and
  requests 2.34.2 are current.
- Documentation check: Sphinx 9.2.0 (`tests/docs/requirements.txt`).
- Upgrade: `cruft update`, `./adm_01_build.sh`, then start again. Instances
  generated with the old image values change them with `cruft update
  --variables-to-update`.

## [26.10.2] - 2026-10-14

- Documentation of the instance in `docs/en` and `docs/de` (Sphinx sources,
  MyST Markdown): index, setup, build and release, operations, security,
  troubleshooting, reference, notebooks. The instance README is now an entry
  point with a quick start, the links, the honesty notes and the license;
  its former sections moved into the documentation.
- `docs/_build/` in `.gitignore` of the instance.
- Template CI: `tests/check_docs.py` checks that both languages match and
  build without warnings (`tests/docs/conf.py`, `tests/docs/requirements.txt`).
- This changelog.
