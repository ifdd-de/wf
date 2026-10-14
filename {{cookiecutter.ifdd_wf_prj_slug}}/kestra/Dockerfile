# Kestra image of this instance: the pinned upstream image plus
#   - the instance's CA certificates (certs/) in the system trust store, for
#     Python processes of the Process task runner. Kestra's JVM keeps its own
#     trust store and is not changed;
#   - the Python packages of kestra/requirements.txt for those processes.
#
# Build context is the instance root (see .dockerignore); built by
# adm_01_build.sh, never published.
ARG KESTRA_IMAGE
FROM ${KESTRA_IMAGE}

USER root

COPY build/install-certs.sh /usr/local/sbin/ifdd-install-certs
COPY certs/ /tmp/ifdd-certs/
RUN sh /usr/local/sbin/ifdd-install-certs /tmp/ifdd-certs

# Python's ssl module, requests (which otherwise uses its own certifi bundle)
# and pip use the system bundle, including the certificates above.
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

# The upstream image (2.0.4) puts /app/.venv/bin first on PATH, so `python` in
# a Process task is that virtual environment when it exists; the packages must
# go there. Without it, the system python3 is used.
COPY kestra/requirements.txt /tmp/requirements.txt
RUN set -eu; \
    if [ -x /app/.venv/bin/python ]; then PY=/app/.venv/bin/python; else PY=python3; fi; \
    echo "Python of the Process task runner: $PY ($($PY --version 2>&1))"; \
    if $PY -m pip --version >/dev/null 2>&1; then \
        PIP_BREAK_SYSTEM_PACKAGES=1 $PY -m pip install --no-cache-dir -r /tmp/requirements.txt; \
    elif command -v uv >/dev/null 2>&1; then \
        uv pip install --python "$PY" --no-cache -r /tmp/requirements.txt; \
    elif $PY -m ensurepip --upgrade >/dev/null 2>&1; then \
        PIP_BREAK_SYSTEM_PACKAGES=1 $PY -m pip install --no-cache-dir -r /tmp/requirements.txt; \
    else \
        echo "No pip, uv or ensurepip for $PY - adjust kestra/Dockerfile" >&2; exit 1; \
    fi; \
    rm /tmp/requirements.txt; \
    $PY -c "import pandas, requests, sqlalchemy; print('packages ok')"

# Root on purpose: the compose files run Kestra as root anyway (Docker socket,
# see README). Kept explicit so that a later switch to a non-root user is a
# visible change here.
USER root
