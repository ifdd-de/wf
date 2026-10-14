(ifdd-wf-security)=
# Security
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

Whoever can edit flows can run code in containers with Docker access. Treat
access to Kestra like administrative access to the host.

## Access

{% if sso -%}
- The router passes every request through the login gate of the proxy
  (forwardAuth to oauth2-proxy with `allowed_groups={{ cookiecutter.ifdd_wf_sso_group }}`):
  browsers without a session are sent to Keycloak, signed-in users outside
  the group get 403.
- Kestra's own login (basic authentication, `IFDD_WF_ADMIN_USER`) stays as a
  second factor; all members of the group share this one Kestra account.
{%- else -%}
- There is no login gate in front of Kestra in this instance
  (`ifdd_wf_enable_sso`); Kestra's own login (basic authentication,
  `IFDD_WF_ADMIN_USER`) is the only protection. Everyone who knows it shares
  one Kestra account.
{%- endif %}
- Kestra is served at the root of its own host name, never under a path
  prefix: Kestra 2.0.4 does not authenticate its API under a context path,
  and its UI then calls the API without the prefix, so the login fails.

## Docker access

{% if dind -%}
Task containers run in a privileged Docker-in-Docker container. It is root
on the host's kernel, but keeps the host's own Docker daemon out of reach.
The daemon listens only on a unix socket in a volume shared with Kestra, not
on TCP. The `dind` container is on `{{ cookiecutter.ifdd_proxy_network }}`:
task containers with `networkMode: host` reach every service on that
network, as any container there can.
{%- else -%}
The host's Docker socket is mounted into Kestra. This gives Kestra, and
every flow, root-equivalent control of the host.
{%- endif %} Kestra itself runs as root (needed for the Docker socket).

## Secrets

- `.env` holds Kestra's login, the database password and the encryption key;
  `secrets/kestra.env` the flow secrets and variables. Both are git-ignored
  and on the recommended skip list.
- Every variable in `secrets/kestra.env` is visible to every flow and to
  every process the Process task runner starts.
- The client `{{ cookiecutter.ifdd_keycloak_api_client_id }}` may only read.
  Its secret reaches a notebook as an environment variable, never as a
  papermill parameter: parameters are written into the executed notebook.
- The Git token should have write access to the content repository only.

## Network and ports

The management port 8081 (health, metrics) is unauthenticated and never
published. PostgreSQL is only on the internal network `db`. In production
no port is published; Kestra is reached through the proxy only.
