{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" -%}
# {{ cookiecutter.ifdd_wf_prj_name }}

Kestra {{ cookiecutter.ifdd_wf_kestra_image.split(":")[-1] }} (open-source edition) with PostgreSQL, generated from
`ifdd-de/wf`. Production URL: `https://<IFDD_WF_HOST>/`.

## Quick start

```bash
cp <proxy instance>/certs/ca.crt certs/      # with the local CA of the proxy
# fill in secrets/kestra.env (Git token and repository, client secret)
./adm_01_build.sh production
./adm_02_run.sh production
```

Then log in{% if sso %} (Keycloak first, then{% else %} with{% endif %} `IFDD_WF_ADMIN_USER` and
`IFDD_WF_ADMIN_PASSWORD` from `.env`{% if sso %}){% endif %}.

## Documentation

Setup, build and release, operations, security, troubleshooting, reference
and notebooks of this instance:

- English: [docs/en/index.md](docs/en/index.md)
- Deutsch: [docs/de/index.md](docs/de/index.md)

The pages are Sphinx sources in MyST Markdown, meant to be copied into a
documentation project that covers all services; GitHub shows them as plain
Markdown.

## Honesty notes

The Dockerfiles were not built while writing the template (no Docker in that
environment). See the template README for what was verified, and the notes marked
"Not tested" in the documentation.

Backend example (2026-10-09): the notebook ran with papermill 2.7.0 against a
real ifdd-be (be-core with PostgreSQL 18.4) and Keycloak 26.8.0 (template
realm, client `ifdd-api-script`): 7 products, 3 locations; a wrong secret,
a missing variable, an unknown segment and a client without read access
end with a clear message; over HTTPS it needs `REQUESTS_CA_BUNDLE` with the
local CA and then works. Kestra 2.0.4 (release binary, plugin-script-python
1.14.0) validated both example flows and refused a misspelt `networkMode`;
the flow ran in Kestra with the Process task runner instead of Docker
(`envs.*`, `secret()`, namespace file, output files `count.json` and
`executed.ipynb`), and the secret appeared neither in the logs nor in the
output files. Not verified: the Docker task runner, `networkMode`, and
name resolution inside DinD (no Docker).

## License

BSD-3-Clause, see `LICENSE`.
