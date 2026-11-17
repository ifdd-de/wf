(ifdd-wf-index)=
# {{ cookiecutter.ifdd_wf_prj_name }} (wf)
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

Der Workflow-Dienst eines IFDD-Knotens: Kestra (Open-Source-Edition) mit
PostgreSQL führt Flows aus, startet Task-Container, führt Jupyter-Notebooks
mit papermill aus und hält seine Flows in einem Git-Inhalts-Repository. Dieses
Kapitel beschreibt die Instanz `{{ cookiecutter.ifdd_wf_prj_slug }}`, erzeugt
aus dem Template `ifdd-de/wf`, aus Sicht derer, die sie einrichten, bauen,
betreiben und absichern.

| | |
|---|---|
| URL | `https://{{ cookiecutter.ifdd_wf_host }}/` (Vorgabe von `IFDD_WF_HOST`; vom Proxy geroutet, immer an der Wurzel eines eigenen Hosts) |
| Kestra | `{{ cookiecutter.ifdd_wf_kestra_image }}`, Datenbank `{{ cookiecutter.ifdd_wf_postgres_image }}` |
| Task-Container | {% if dind %}in einem eigenen Docker-in-Docker-Daemon (`{{ cookiecutter.ifdd_wf_dind_image }}`){% else %}im Docker-Daemon des Hosts (Socket eingebunden){% endif %} |
| Zugang | {% if sso %}Login-Gate des Proxys (Keycloak-Gruppe `{{ cookiecutter.ifdd_wf_sso_group }}`), dann die eigene Anmeldung von Kestra{% else %}nur die eigene Anmeldung von Kestra{% endif %} |
| Backend für Flows | `{{ cookiecutter.ifdd_be_url }}`, Client `{{ cookiecutter.ifdd_keycloak_api_client_id }}` (nur lesend) |
| Entwicklung | `http://127.0.0.1:{{ cookiecutter.ifdd_wf_dev_port }}/` |
| Inhalts-Repository | `{{ cookiecutter.ifdd_wf_git_url }}`, Branch `{{ cookiecutter.ifdd_wf_git_branch }}`, Wurzel-Namespaces `{{ cookiecutter.ifdd_wf_git_namespaces }}` (Produktion) |

## Was die Instanz enthält

Zwei Compose-Dateien; das Kestra-Image (`kestra/`: `Dockerfile`,
`requirements.txt` für Process-Tasks, `application.yml`){% if dind %}, das
Docker-in-Docker-Image (`dind/`){% endif %} und das papermill-Runner-Image
(`runners/papermill/`), alle lokal gebaut und mit den CA-Zertifikaten aus
`certs/` im Trust-Store; `.env` und `secrets/kestra.env` mit erzeugten
Werten; die Flows der Git-Synchronisation (`flows/system/`) und ihr
Hilfsskript `kestra/git_sync.py`; Beispiel-Flows und -Notebooks; die
Skripte `adm_01_build.sh`, `adm_02_run.sh`, `adm_03_git_push.sh` und
`adm_99_destroy.sh`.

## Architektur

```{uml}
@startuml
left to right direction
{%- if sso %}
  rectangle "Browser" as Browser
  rectangle "proxy: Traefik" as Proxy
  rectangle "oauth2-proxy" as OAuth2
  Browser --> Proxy : HTTPS
  Proxy --> OAuth2 : forwardAuth
{%- else %}
  rectangle "Browser" as Browser
  rectangle "proxy: Traefik" as Proxy
  Browser --> Proxy : HTTPS
{%- endif %}
  rectangle "kestra" as Kestra
  Proxy --> Kestra
  database "PostgreSQL" as PG
  Kestra --> PG : Netz db
{%- if dind %}
  rectangle "dind: Docker-Daemon" as DinD
  Kestra --> DinD : Socket-Volume
  rectangle "Task-Container" as Tasks
  DinD --> Tasks
{%- else %}
  rectangle "Docker des Hosts" as Docker
  rectangle "Task-Container" as Tasks
  Kestra --> Docker : Host-Socket
  Docker --> Tasks
{%- endif %}
  Tasks --> Proxy : über den Proxy: be, Keycloak
  rectangle "Inhalts-Repository" as Git
  Kestra --> Git : Push, stündlich
  Git --> Kestra : Restore beim Start
@enduml
```

| Wer | Nutzt wf für |
|---|---|
| Menschen in der Gruppe `{{ cookiecutter.ifdd_wf_sso_group }}` | Flows in der Kestra-Oberfläche bearbeiten und ausführen |
| Flows und Notebooks | Lesen des Backends mit dem Client `{{ cookiecutter.ifdd_keycloak_api_client_id }}` |

## Kapitel

```{toctree}
:maxdepth: 2

setup
build-release
operations
security
troubleshooting
reference
notebooks
```

Die Werte der Variablen dieser Instanz und ihre Beziehungen zu den anderen
Diensten stehen im Kapitel über die Dienst-Instanzen
({ref}`ifdd-instances-wf`).
