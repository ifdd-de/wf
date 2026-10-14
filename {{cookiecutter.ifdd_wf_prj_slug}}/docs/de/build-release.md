(ifdd-wf-build-release)=
# Bauen und Freigeben
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}

## Images

| Image | Aus | Gebaut aus |
|---|---|---|
| `{{ cookiecutter.ifdd_wf_prj_slug }}-kestra:local` | `{{ cookiecutter.ifdd_wf_kestra_image }}` | `kestra/Dockerfile`: die CAs aus `certs/` und die Python-Pakete aus `kestra/requirements.txt` für Process-Tasks |
{%- if dind %}
| `{{ cookiecutter.ifdd_wf_prj_slug }}-dind:local` | `{{ cookiecutter.ifdd_wf_dind_image }}` | `dind/Dockerfile`: die CAs aus `certs/` |
{%- endif %}
| `IFDD_WF_RUNNER_PAPERMILL_IMAGE` (Vorgabe `{{ cookiecutter.ifdd_wf_prj_slug }}-papermill:local`) | `{{ cookiecutter.ifdd_wf_runner_python_image }}` | `runners/papermill/Dockerfile`: papermill und die Notebook-Pakete |
| PostgreSQL | `{{ cookiecutter.ifdd_wf_postgres_image }}` | Upstream, nicht gebaut |

```bash
./adm_01_build.sh production     # oder development
```

Das Skript baut alle Images mit `--pull`, damit Sicherheitskorrekturen
beweglicher Basis-Images ankommen. Nach einer Änderung an `certs/`,
`kestra/`, {% if dind %}`dind/`, {% endif %}`runners/` oder einer
Image-Version erneut ausführen. `build/install-certs.sh` fügt jede `*.crt`
und `*.pem` aus `certs/` dem System-Trust-Store jedes Images hinzu; die
Java-Laufzeit von Kestra hält einen eigenen Trust-Store und nutzt sie nicht.
{%- if dind %}

Die Runner-Images sind lokal. Der Docker-in-Docker-Daemon hat einen eigenen
Image-Speicher und kann sie nicht ziehen: `adm_02_run.sh` lädt sie bei jedem
Start hinein.
{%- endif %}

Python-Pakete für Notebooks: siehe die Kommentare in
`runners/papermill/Dockerfile`.

## Versionen

Die Image-Tags sind Template-Variablen (siehe {ref}`ifdd-instances-wf`). Die
Kestra-Version ist die 2.0-Linie (`{{ cookiecutter.ifdd_wf_kestra_image }}`);
das Template wurde mit dem Release-Binary von Kestra 2.0.4 geprüft.

## Tests

```bash
pip install -r tests/requirements.txt
pytest -q tests
```

Die statischen Prüfungen decken die Konfiguration ab: kein veröffentlichter
Management-Port, keine wörtlichen Secrets, stimmige Pfade, der gewählte
Docker-Zugriff und dass die erzeugten Secrets die Regeln von Kestra
erfüllen.

## CI der Instanz

`.github/workflows/ci.yml` legt Platzhalter für die erzeugten, nicht
committeten Dateien an, führt die statischen Prüfungen aus und validiert
beide Compose-Dateien.

## Freigabe

Es gibt keinen Release-Workflow: Die Images werden auf dem Host gebaut, der
sie betreibt.

```{note}
Nicht getestet: Die drei Dockerfiles wurden für das Template nicht gebaut
(kein Docker in dieser Umgebung); insbesondere ob das Kestra-Image pip in
`/app/.venv` hat{% if dind %}, und das Laden des Runner-Images in den
Docker-in-Docker-Daemon{% endif %}.
```
