# Runner image for Jupyter notebooks, executed with papermill by Kestra's
# Docker task runner (see examples/flows/papermill_example.yml).
#
# LOCAL ONLY. Built by adm_01_build.sh and never pushed to a registry: it
# carries the instance's CA certificates. Its tag comes from
# IFDD_WF_RUNNER_PAPERMILL_IMAGE in .env; flows read it as
# {% raw %}{{ envs.runner_papermill_image }}{% endraw %} and must use pullPolicy: NEVER.
# With Docker-in-Docker, adm_02_run.sh loads it into the DinD daemon.
#
# EXTENDING
#   - More packages: add them, pinned, to runners/papermill/requirements.txt,
#     then ./adm_01_build.sh <mode> and ./adm_02_run.sh <mode>.
#   - System packages (e.g. for database drivers): add an apt-get line below
#     the certificate step; keep `--no-install-recommends` and clean
#     /var/lib/apt/lists in the same RUN.
#   - Another runner: copy this directory to runners/<name>/, add a service
#     with profile "runners" to both compose files and a variable
#     IFDD_WF_RUNNER_<NAME>_IMAGE to .env, secrets/kestra.env (ENV_...) and
#     adm_02_run.sh.
#
# Build context is the instance root (see .dockerignore).
ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}

COPY build/install-certs.sh /usr/local/sbin/ifdd-install-certs
COPY certs/ /tmp/ifdd-certs/
RUN sh /usr/local/sbin/ifdd-install-certs /tmp/ifdd-certs

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    PYTHONDONTWRITEBYTECODE=1

COPY runners/papermill/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt \
    && python -m ipykernel install --sys-prefix --name python3 \
    && papermill --version
