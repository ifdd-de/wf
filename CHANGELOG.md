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
- Git synchronisation in both directions (production only). The flows
  `flows/system/git_push.yml` and `git_restore.yml` replace
  `examples/flows/system_git_sync.yml` and are no longer imported by hand:
  `adm_02_run.sh production` loads them through Kestra's API, restores every
  root namespace that has no flow from the content repository, and loads the
  hourly push only when every restore succeeded, so a newly built, empty
  instance cannot push over the repository. The push now deletes in Git what
  was deleted in Kestra (`whenMissingInSource: DELETE`, was `KEEP`) and never
  runs twice at the same time. The restore handles child namespaces one by
  one, because the open-source edition cannot create namespaces through its
  API (Kestra 2.0.8, plugin-git 4.6.3).
- New template variables `ifdd_wf_git_url`, `ifdd_wf_git_username`,
  `ifdd_wf_git_branch`, `ifdd_wf_git_namespaces`, checked by the pre-hook
  and passed as `ENV_GIT_*` in `docker-compose-production.yml`; only the
  token stays in `secrets/kestra.env` (`SECRET_GIT_TOKEN`).
  `adm_02_run.sh production` refuses to start without it.
- `kestra/application.yml`: `kestra.tasks.sdk.authentication` points tasks
  that call Kestra's API (NamespaceSync) to `http://localhost:8080` with
  Kestra's login. Before, they used `kestra.url`, the public URL behind the
  proxy and the login gate.
- The CA certificates of `certs/` also go into the Java trust store of the
  Kestra image (`build/install-java-certs.sh`), one certificate at a time,
  so bundles work; needed for Git behind a TLS-inspecting proxy.
- New scripts `adm_03_git_push.sh` (push now and wait) and
  `adm_99_destroy.sh` (push, then remove containers, volumes, local images
  and the instance directory), helper `kestra/git_sync.py`.
- Upgrade: `cruft update --variables-to-update` with the four `ifdd_wf_git_*`
  values, move the token to `SECRET_GIT_TOKEN` if it is not there, remove
  the `ENV_GIT_*` lines from `secrets/kestra.env` (the compose values win
  anyway), delete the flow `system.git_sync` in the UI, then
  `./adm_01_build.sh production` and `./adm_02_run.sh production`.

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
