(ifdd-wf-build-release)=
# Build and release
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}

## Images

| Image | From | Built from |
|---|---|---|
| `{{ cookiecutter.ifdd_wf_prj_slug }}-kestra:local` | `{{ cookiecutter.ifdd_wf_kestra_image }}` | `kestra/Dockerfile`: the CAs of `certs/` and the Python packages of `kestra/requirements.txt` for Process tasks |
{%- if dind %}
| `{{ cookiecutter.ifdd_wf_prj_slug }}-dind:local` | `{{ cookiecutter.ifdd_wf_dind_image }}` | `dind/Dockerfile`: the CAs of `certs/` |
{%- endif %}
| `IFDD_WF_RUNNER_PAPERMILL_IMAGE` (default `{{ cookiecutter.ifdd_wf_prj_slug }}-papermill:local`) | `{{ cookiecutter.ifdd_wf_runner_python_image }}` | `runners/papermill/Dockerfile`: papermill and the notebook packages |
| PostgreSQL | `{{ cookiecutter.ifdd_wf_postgres_image }}` | upstream, not built |

```bash
./adm_01_build.sh production     # or development
```

The script builds all images with `--pull`, so security fixes of moving
base images are picked up. Run it again after a change of `certs/`,
`kestra/`, {% if dind %}`dind/`, {% endif %}`runners/` or an image version.
`build/install-certs.sh` adds every `*.crt` and `*.pem` of `certs/` to the
system trust store of each image; Kestra's Java runtime keeps its own trust
store and does not use them.
{%- if dind %}

The runner images are local. The Docker-in-Docker daemon has its own image
store and cannot pull them: `adm_02_run.sh` loads them into it on every
start.
{%- endif %}

To add Python packages to notebooks, see the comments in
`runners/papermill/Dockerfile`.

## Versions

The image tags are template variables (see {ref}`ifdd-instances-wf`). The
Kestra version is the 2.0 line (`{{ cookiecutter.ifdd_wf_kestra_image }}`);
the template was checked with the Kestra 2.0.4 release binary.

## Tests

```bash
pip install -r tests/requirements.txt
pytest -q tests
```

The static checks cover the configuration: no published management port,
no literal secrets, consistent paths, the chosen Docker access, and that the
generated secrets meet Kestra's rules.

## CI of the instance

`.github/workflows/ci.yml` creates stand-ins for the generated files that
are not committed, runs the static checks and validates both compose files.

## Release

There is no release workflow: the images are built on the host that runs
them.

```{note}
Not tested: the three Dockerfiles have not been built for the template (no
Docker in that environment); in particular whether the Kestra image has pip
in `/app/.venv`{% if dind %}, and loading the runner image into the
Docker-in-Docker daemon{% endif %}.
```
