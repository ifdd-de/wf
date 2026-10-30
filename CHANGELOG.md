# Changelog

The version scheme follows the other IFDD templates: `YY.MM.N`.

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
