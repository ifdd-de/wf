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
    "ifdd_proxy_oauth2_proxy_service": "{{ cookiecutter.ifdd_proxy_oauth2_proxy_service }}",
    "ifdd_wf_git_url": "{{ cookiecutter.ifdd_wf_git_url }}",
    "ifdd_wf_git_username": "{{ cookiecutter.ifdd_wf_git_username }}",
    "ifdd_wf_git_branch": "{{ cookiecutter.ifdd_wf_git_branch }}",
    "ifdd_wf_git_namespaces": "{{ cookiecutter.ifdd_wf_git_namespaces }}",
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
    # Shared with ifdd-de/proxy, which names its Traefik service so; this
    # template appends @docker.
    "ifdd_proxy_oauth2_proxy_service": (r"[A-Za-z0-9_-]+", "the Traefik service of oauth2-proxy without @docker, as in ifdd-de/proxy"),
    # Git synchronisation (flows/system/): HTTPS only, the token is the password.
    "ifdd_wf_git_url": (r"https://[A-Za-z0-9.-]+(:[0-9]+)?/[^\s@]*[^\s@/]", "an https:// URL of the content repository, without credentials"),
    "ifdd_wf_git_username": (r"[A-Za-z0-9][A-Za-z0-9_.-]*", "a Git user name (no spaces, no @)"),
    "ifdd_wf_git_branch": (r"[A-Za-z0-9][A-Za-z0-9_./-]*", "a branch name without refs/heads/ or origin/"),
    # Kestra's namespace pattern (Flow.namespace, Kestra 2.0.8), comma separated.
    "ifdd_wf_git_namespaces": (r"[a-z0-9][a-z0-9._-]*(,[a-z0-9][a-z0-9._-]*)*", "root namespaces separated by commas, no spaces"),
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

# Deprecated: ifdd_wf_sso_service gave the service of the login callback.
# A value other than its old default still wins, so existing instances keep
# their router; the shared ifdd_proxy_oauth2_proxy_service replaces it.
if values["ifdd_wf_enable_sso"] == "y" and values["ifdd_wf_sso_service"] != "oauth2-proxy@docker":
    print(
        f"WARNING: ifdd_wf_sso_service={values['ifdd_wf_sso_service']!r} is deprecated and still used; "
        "set ifdd_proxy_oauth2_proxy_service (shared with ifdd-de/proxy) to the name without @docker "
        "and ifdd_wf_sso_service back to oauth2-proxy@docker",
        file=sys.stderr,
    )

branch = values["ifdd_wf_git_branch"]
if ".." in branch or branch.endswith((".lock", "/", ".")) or "//" in branch or branch.startswith(("refs/", "origin/")):
    errors.append(f"ifdd_wf_git_branch={branch!r}: expected a branch name without refs/ or origin/, '..', '//' or a trailing .lock, / or .")

# Each root namespace is synchronised with its child namespaces. A root
# inside another root would be synchronised twice; "system" holds the
# synchronisation flows themselves and is never synchronised.
namespaces = values["ifdd_wf_git_namespaces"].split(",")
for ns in namespaces:
    if ns == "system" or ns.startswith("system."):
        errors.append(f"ifdd_wf_git_namespaces: {ns!r} is reserved for the synchronisation flows")
    if len(ns) > 150:
        errors.append(f"ifdd_wf_git_namespaces: {ns!r} is longer than 150 characters")
    for other in namespaces:
        if other != ns and other.startswith(ns + "."):
            errors.append(f"ifdd_wf_git_namespaces: {other!r} lies inside {ns!r}; list only the root")
if len(set(namespaces)) != len(namespaces):
    errors.append("ifdd_wf_git_namespaces: a namespace is listed twice")

if errors:
    print("Invalid template values:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    sys.exit(1)
