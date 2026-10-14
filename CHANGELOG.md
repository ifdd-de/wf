# Changelog

The version scheme follows the other IFDD templates: `YY.MM.N`.

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
