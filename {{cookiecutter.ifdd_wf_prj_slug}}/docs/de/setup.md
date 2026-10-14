(ifdd-wf-setup)=
# Einrichtung
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

## Voraussetzungen

| Was | Warum |
|---|---|
| Docker mit Compose | Kestra, PostgreSQL{% if dind %}, der Docker-in-Docker-Daemon{% endif %} und die Runner laufen als Container; die Images werden lokal gebaut |
| das externe Netz `{{ cookiecutter.ifdd_proxy_network }}` und eine laufende Proxy-Instanz | Traefik routet `IFDD_WF_HOST` zu Kestra; Task-Container erreichen darüber die anderen Dienste |
{%- if sso %}
| das Login-Gate des Proxys (`ifdd_proxy_enable_oauth2_proxy=y`) mit der Redirect-URI `https://<IFDD_WF_HOST>/oauth2/callback` in seinem Client | jede Anfrage geht durch oauth2-proxy |
| die Keycloak-Gruppe `{{ cookiecutter.ifdd_wf_sso_group }}` | ihre Mitglieder kommen durch das Gate |
{%- endif %}
| das CA-Zertifikat des Proxys, wenn er eine eigene CA nutzt | es wird in die Images gebaut |
| ein Git-Inhalts-Repository und ein Token nur mit Schreibrecht darauf | die Flows werden dorthin geschoben |

## Instanz anlegen

Üblicherweise legt das Meta-Repository alle Instanzen in einem Zug an
(`.adm_meta_01_all.sh`, Schritt `.adm_01_create_services.sh`): Es ruft
`cruft create` mit der gemeinsamen Variablendatei `.cookiecutter_all.yaml`
auf, kopiert `certs/ca.crt` des Proxys nach `certs/` und das Secret des
Clients `{{ cookiecutter.ifdd_keycloak_api_client_id }}` nach
`secrets/kestra.env`. Von Hand, im Verzeichnis der Instanzen, mit der
Skip-Liste, die dieses Template empfiehlt:

```bash
cruft create --no-input --config-file .cookiecutter_all.yaml \
  --skip .env --skip secrets --skip certs \
  https://github.com/ifdd-de/wf
cp proxy/certs/ca.crt {{ cookiecutter.ifdd_wf_prj_slug }}/certs/
```

Das Meta-Repository übergibt `--skip envs --skip .env`.

## Konfiguration und Secrets

Der Post-Generation-Hook legt `.env` und `secrets/kestra.env` aus ihren
`.dist`-Dateien an und füllt jeden Platzhalter `<<generate:...>>` mit einem
Zufallswert; vorhandene Dateien werden nie überschrieben.

| Datei | Enthält |
|---|---|
| `.env` | Host, Entwicklungsport, die Anmeldung von Kestra (`IFDD_WF_ADMIN_USER`, `IFDD_WF_ADMIN_PASSWORD`), Datenbankpasswort, Verschlüsselungsschlüssel, den Tag des Runner-Images |
| `secrets/kestra.env` | Flow-Secrets `SECRET_<NAME>` (Base64) und Flow-Variablen `ENV_<NAME>` (Klartext), an Kestra übergeben |

Von Hand in `secrets/kestra.env` eintragen: das Git-Token
(`SECRET_GIT_TOKEN`, Base64), `ENV_GIT_URL`, `ENV_GIT_USERNAME`,
`ENV_GIT_BRANCH` und das Secret von
`{{ cookiecutter.ifdd_keycloak_api_client_id }}`
(`SECRET_IFDD_API_CLIENT_SECRET`, Base64; dieses trägt das Meta-Repository
ein). Ohne abschließenden Zeilenumbruch kodieren:
`printf '%s' 'value' | base64 -w0`. Die Einträge stehen in
{ref}`ifdd-wf-reference`, die Template-Variablen in
{ref}`ifdd-instances-wf`.

## Erster Start

```bash
./adm_01_build.sh production
./adm_02_run.sh production
```

Dann `https://<IFDD_WF_HOST>/` öffnen und anmelden{% if sso %} (zuerst
Keycloak, dann{% else %} mit{% endif %} `IFDD_WF_ADMIN_USER` und
`IFDD_WF_ADMIN_PASSWORD` aus `.env`{% if sso %}){% endif %}.
`examples/flows/system_git_sync.yml` nach Anpassen seiner Namespace-Liste
importieren, einmal ausführen und das Inhalts-Repository prüfen.

Die Datenbank startet leer. Flows einer älteren Instanz in der Oberfläche
oder über die API importieren; Kestra 2.0 hat mehrere Task-Typen geändert
(etwa `ForEach` -> `Loop`), daher den Migrationsleitfaden von Kestra für 2.0
prüfen.

## Lokale Entwicklung

```bash
./adm_01_build.sh development
./adm_02_run.sh development
```

Kestra liegt dann unter `http://127.0.0.1:{{ cookiecutter.ifdd_wf_dev_port }}/`
mit den Anmeldedaten aus `.env`: kein Proxy, kein Login-Gate, und weder
Kestra noch die Task-Container hängen im Proxy-Netz.
