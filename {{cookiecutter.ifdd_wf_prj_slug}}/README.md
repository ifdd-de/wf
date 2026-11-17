{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" -%}
# {{ cookiecutter.ifdd_wf_prj_name }}

Kestra {{ cookiecutter.ifdd_wf_kestra_image.split(":")[-1] }} (open-source edition) with PostgreSQL, generated from
`ifdd-de/wf`. Production URL: `https://<IFDD_WF_HOST>/`.

## Quick start

```bash
cp <proxy instance>/certs/ca.crt certs/      # with the local CA of the proxy
# fill in secrets/kestra.env (Git token, client secret)
./adm_01_build.sh production
./adm_02_run.sh production
```

Then log in{% if sso %} (Keycloak first, then{% else %} with{% endif %} `IFDD_WF_ADMIN_USER` and
`IFDD_WF_ADMIN_PASSWORD` from `.env`{% if sso %}){% endif %}.

In production the flows are kept in the content repository
`{{ cookiecutter.ifdd_wf_git_url }}` (branch `{{ cookiecutter.ifdd_wf_git_branch }}`):
`./adm_02_run.sh production` restores them into an empty Kestra and then
pushes hourly, `./adm_03_git_push.sh` pushes at once, and
`./adm_99_destroy.sh` pushes and then deletes the instance completely.

## Documentation

Setup, build and release, operations, security, troubleshooting, reference
and notebooks of this instance:

- English: [docs/en/index.md](docs/en/index.md)
- Deutsch: [docs/de/index.md](docs/de/index.md)

The pages are Sphinx sources in MyST Markdown, meant to be copied into a
documentation project that covers all services; GitHub shows them as plain
Markdown.

## AI assistance

Some parts of the template `ifdd-de/wf` this instance was generated
from, in particular the tests, the test data and the documentation, were
developed or improved with the help of large language models (LLMs). All
changes were reviewed and released by the maintainer.

## License

BSD-3-Clause, see `LICENSE`.
