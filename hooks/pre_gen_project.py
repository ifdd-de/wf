"""Reject values that would render but not work.

A mistake shows up here and not later as a container that does not start, a
router Traefik drops or a login that never succeeds.
"""

import re
import sys

values = {
    "ifdd_wf_prj_slug": "{{ cookiecutter.ifdd_wf_prj_slug }}",
    "ifdd_wf_host": "{{ cookiecutter.ifdd_wf_host }}",
    "ifdd_wf_entrypoint": "{{ cookiecutter.ifdd_wf_entrypoint }}",
    "ifdd_wf_dev_port": "{{ cookiecutter.ifdd_wf_dev_port }}",
    "ifdd_wf_admin_email": "{{ cookiecutter.ifdd_wf_admin_email }}",
    "ifdd_wf_kestra_image": "{{ cookiecutter.ifdd_wf_kestra_image }}",
    "ifdd_wf_postgres_image": "{{ cookiecutter.ifdd_wf_postgres_image }}",
    "ifdd_wf_docker_mode": "{{ cookiecutter.ifdd_wf_docker_mode }}",
    "ifdd_wf_dind_image": "{{ cookiecutter.ifdd_wf_dind_image }}",
    "ifdd_wf_runner_python_image": "{{ cookiecutter.ifdd_wf_runner_python_image }}",
    "ifdd_wf_docker_volume_enabled": "{{ cookiecutter.ifdd_wf_docker_volume_enabled }}",
    "ifdd_wf_enable_sso": "{{ cookiecutter.ifdd_wf_enable_sso }}",
    "ifdd_wf_sso_group": "{{ cookiecutter.ifdd_wf_sso_group }}",
    "ifdd_wf_sso_auth_address": "{{ cookiecutter.ifdd_wf_sso_auth_address }}",
    "ifdd_wf_sso_service": "{{ cookiecutter.ifdd_wf_sso_service }}",
    "ifdd_proxy_network": "{{ cookiecutter.ifdd_proxy_network }}",
    "ifdd_be_url": "{{ cookiecutter.ifdd_be_url }}",
    "ifdd_oidc_realm": "{{ cookiecutter.ifdd_oidc_realm }}",
    "ifdd_keycloak_api_client_id": "{{ cookiecutter.ifdd_keycloak_api_client_id }}",
}

NAME = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
IMAGE = r"[^\s:@]+(:[^\s:@]+)?(@sha256:[0-9a-f]{64})?"
rules = {
    "ifdd_wf_prj_slug": (r"[a-z0-9][a-z0-9_-]*", "lowercase letters, digits, - and _ (compose project name)"),
    "ifdd_wf_host": (r"[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?", "a host name without scheme, port or path"),
    "ifdd_wf_entrypoint": (NAME, "a Traefik entry point name"),
    "ifdd_wf_dev_port": (r"[0-9]+", "a port number"),
    # Kestra checks the user name of the basic authentication against this
    # pattern (BasicAuthService, Kestra 2.0.4) and refuses to start otherwise.
    "ifdd_wf_admin_email": (r"[a-zA-Z0-9_!#$%&'*+/=?`{|}~^.-]+@[a-zA-Z0-9.-]+", "an email address (Kestra requires one)"),
    "ifdd_wf_kestra_image": (IMAGE, "an image reference"),
    "ifdd_wf_postgres_image": (IMAGE, "an image reference"),
    "ifdd_wf_docker_mode": (r"dind|socket", "dind or socket"),
    "ifdd_wf_dind_image": (IMAGE, "an image reference"),
    "ifdd_wf_runner_python_image": (IMAGE, "an image reference"),
    "ifdd_wf_docker_volume_enabled": (r"[yn]", "y or n"),
    "ifdd_wf_enable_sso": (r"[yn]", "y or n"),
    "ifdd_wf_sso_group": (r"[A-Za-z0-9_./-]+", "a Keycloak group name (no spaces, no commas)"),
    "ifdd_wf_sso_auth_address": (r"https?://[A-Za-z0-9.-]+(:[0-9]+)?", "http(s)://host[:port] of oauth2-proxy, no path, no trailing slash"),
    "ifdd_wf_sso_service": (r"[A-Za-z0-9_-]+@[a-z]+", "a Traefik service reference such as oauth2-proxy@docker"),
    "ifdd_proxy_network": (NAME, "a Docker network name"),
    # Read by flows and notebooks (secrets/kestra.env); paths are appended.
    "ifdd_be_url": (r"https?://[A-Za-z0-9.-]+(:[0-9]+)?(/[^\s]*[^/\s])?", "the URL of ifdd-be without trailing slash"),
    "ifdd_oidc_realm": (r"https?://[A-Za-z0-9.-]+(:[0-9]+)?(/[^\s/]+)*/realms/[^\s/]+", "a Keycloak realm URL without trailing slash"),
    "ifdd_keycloak_api_client_id": (NAME, "a Keycloak client id"),
}

errors = []
for key, (pattern, meaning) in rules.items():
    if not re.fullmatch(pattern, values[key]):
        errors.append(f"{key}={values[key]!r}: expected {meaning}")

port = values["ifdd_wf_dev_port"]
if port.isdigit() and not 1024 <= int(port) <= 65535:
    errors.append(f"ifdd_wf_dev_port={port}: expected a port between 1024 and 65535")

if errors:
    print("Invalid template values:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    sys.exit(1)
