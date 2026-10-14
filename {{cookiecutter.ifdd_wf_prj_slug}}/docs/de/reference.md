(ifdd-wf-reference)=
# Referenz
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

Die Variablen des Templates und ihre Werte in dieser Instanz stehen in
{ref}`ifdd-instances-wf`. Diese Seite führt auf, was keine Template-Variable
ist.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `docker-compose-production.yml` | hinter dem Proxy (`{{ cookiecutter.ifdd_proxy_network }}`){% if sso %}, mit dem Login-Gate (Keycloak-Gruppe `{{ cookiecutter.ifdd_wf_sso_group }}`){% endif %} |
| `docker-compose-development.yml` | `http://127.0.0.1:{{ cookiecutter.ifdd_wf_dev_port }}/`, kein Proxy |
| `kestra/` | Image (`Dockerfile`, `requirements.txt` für Process-Tasks) und `application.yml` |
{%- if dind %}
| `dind/` | Docker-in-Docker-Image für Task-Container |
{%- endif %}
| `runners/papermill/` | lokales Runner-Image für Notebooks |
| `build/install-certs.sh` | fügt `certs/*` dem Trust-Store jedes Images hinzu |
| `certs/` | interne CA-Zertifikate (von Git ausgenommen) |
| `secrets/kestra.env` | Flow-Secrets und Flow-Variablen (von Git ausgenommen) |
| `.env` | Host, Ports, erzeugte Passwörter und Schlüssel (von Git ausgenommen) |
| `examples/` | Git-Sync-Flow, papermill-Flow, Backend-Beispiel-Flow und Notebooks |
| `adm_01_build.sh`, `adm_02_run.sh` | bauen; prüfen und starten |

## Umgebung (`.env`)

| Variable | Vorgabe hier | Bedeutung |
|---|---|---|
| `IFDD_WF_HOST` | `{{ cookiecutter.ifdd_wf_host }}` | Host, den der Proxy zu Kestra routet |
| `IFDD_WF_DEV_PORT` | `{{ cookiecutter.ifdd_wf_dev_port }}` | Port auf 127.0.0.1 in der Entwicklung |
| `IFDD_WF_ADMIN_USER` | `{{ cookiecutter.ifdd_wf_admin_email }}` | Anmeldung von Kestra (eine E-Mail-Adresse) |
| `IFDD_WF_ADMIN_PASSWORD` | erzeugt | mindestens 8 Zeichen mit Klein-, Großbuchstabe und Ziffer |
| `IFDD_WF_DB_PASSWORD` | erzeugt | einmal gesetzt |
| `IFDD_WF_ENCRYPTION_KEY` | erzeugt | AES-Schlüssel für geheime Ein- und Ausgaben |
| `IFDD_WF_RUNNER_PAPERMILL_IMAGE` | `{{ cookiecutter.ifdd_wf_prj_slug }}-papermill:local` | Tag des papermill-Runners; Flows lesen ihn als `{% raw %}{{ envs.runner_papermill_image }}{% endraw %}` |

## Flow-Secrets und -Variablen (`secrets/kestra.env`)

| Eintrag | In Flows gelesen als | Inhalt |
|---|---|---|
| `SECRET_<NAME>` (Base64) | `{% raw %}{{ secret('<NAME>') }}{% endraw %}` | Secrets |
| `ENV_<NAME>` (Klartext) | `{% raw %}{{ envs.<name> }}{% endraw %}` (kleingeschrieben) | Variablen |

| Eintrag | Vorgabe hier |
|---|---|
| `SECRET_GIT_TOKEN` | leer |
| `ENV_GIT_URL`, `ENV_GIT_USERNAME`, `ENV_GIT_BRANCH` | Beispielwerte |
| `ENV_IFDD_BE_URL` | `{{ cookiecutter.ifdd_be_url }}` |
| `ENV_IFDD_OIDC_TOKEN_URL` | `{{ cookiecutter.ifdd_oidc_realm }}/protocol/openid-connect/token` |
| `ENV_IFDD_API_CLIENT_ID` | `{{ cookiecutter.ifdd_keycloak_api_client_id }}` |
| `SECRET_IFDD_API_CLIENT_SECRET` | leer |
| `ENV_TASK_NETWORK` | `{% if dind %}host{% else %}{{ cookiecutter.ifdd_proxy_network }}{% endif %}` |

## Container und Netze

| Container | Port | Netze |
|---|---|---|
| `kestra` | 8080 (vom Proxy geroutet; 127.0.0.1:`IFDD_WF_DEV_PORT` in der Entwicklung), 8081 Management, nicht veröffentlicht | default, `db`, `{{ cookiecutter.ifdd_proxy_network }}` |
| `postgres` | 5432 | `db` (intern) |
{%- if dind %}
| `dind` | keiner (Unix-Socket im Volume `dind-socket`) | default, `{{ cookiecutter.ifdd_proxy_network }}` |
{%- endif %}

Volumes: `postgres-data`, `kestra-storage`, `kestra-wd`{% if dind %},
`dind-socket`, `dind-data`{% endif %}.

Router und Dienst: `{{ cookiecutter.ifdd_wf_prj_slug }}`, Regel
`Host(<IFDD_WF_HOST>)`, Entry Point `{{ cookiecutter.ifdd_wf_entrypoint }}`,
Port 8080{% if sso %}; Middleware `{{ cookiecutter.ifdd_wf_prj_slug }}-sso`
(forwardAuth an `{{ cookiecutter.ifdd_wf_sso_auth_address }}`) und der Router
`{{ cookiecutter.ifdd_wf_prj_slug }}-oauth2` für `/oauth2/` an
`{{ cookiecutter.ifdd_wf_sso_service }}`{% endif %}.
