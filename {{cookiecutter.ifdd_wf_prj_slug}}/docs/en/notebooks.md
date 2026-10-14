(ifdd-wf-notebooks)=
# Notebooks

## Papermill

`examples/flows/papermill_example.yml` runs a notebook from the namespace
files in the image `{% raw %}{{ envs.runner_papermill_image }}{% endraw %}`
(`IFDD_WF_RUNNER_PAPERMILL_IMAGE` in `.env`) with `pullPolicy: NEVER`. The
parameter cell of the notebook must carry the tag `parameters`. Packages for
notebooks go into the runner image (see the comments in
`runners/papermill/Dockerfile`, then rebuild).

## Backend example

`examples/flows/backend_product_count.yml` runs
`examples/notebooks/backend_product_count.ipynb`, which asks the backend how
many documents of one collection (input `segment`, default `products`) are
valid now (header `X-Total-Count`) and writes `count.json`. A demo, not a
pattern for every notebook.

1. `secrets/kestra.env`: `ENV_IFDD_BE_URL`, `ENV_IFDD_OIDC_TOKEN_URL` and
   `ENV_IFDD_API_CLIENT_ID` are set at generation; put the secret of that
   client (`IFDD_KEYCLOAK_API_CLIENT_SECRET` of the keycloak instance) into
   `SECRET_IFDD_API_CLIENT_SECRET`, base64-encoded (the meta repository's
   `.adm_01_create_services.sh` does it). Instances generated before these
   lines existed need them added by hand, `ENV_TASK_NETWORK` too.
2. `./adm_02_run.sh production` (Kestra reads `secrets/kestra.env` at
   start).
3. Upload the notebook in the UI (Namespaces -> `ifdd.examples` -> Files) as
   `notebooks/backend_product_count.ipynb`, import the flow, run it.
   `executed.ipynb` and `count.json` are output files of the task.

Production only: in development neither Kestra nor the task containers are
on the proxy network. The client may only read; its secret reaches the task
as an environment variable, never as a papermill parameter.

## Running a notebook outside Kestra

The notebook also runs on a workstation that resolves the service names,
for example from the meta repository, with `papermill`, `ipykernel` and
`requests` installed:

```bash
export IFDD_BE_URL={{ cookiecutter.ifdd_be_url }}
export IFDD_OIDC_TOKEN_URL={{ cookiecutter.ifdd_oidc_realm }}/protocol/openid-connect/token
export IFDD_API_CLIENT_ID={{ cookiecutter.ifdd_keycloak_api_client_id }}
export IFDD_API_CLIENT_SECRET=$(sed -n 's/^IFDD_KEYCLOAK_API_CLIENT_SECRET=//p' keycloak/.env)
export REQUESTS_CA_BUNDLE=$PWD/proxy/certs/ca.crt   # with the local CA
papermill {{ cookiecutter.ifdd_wf_prj_slug }}/examples/notebooks/backend_product_count.ipynb /tmp/executed.ipynb
```

`REQUESTS_CA_BUNDLE` is needed because `requests` uses its own CA bundle
(certifi), not the CAs trusted by the operating system.
