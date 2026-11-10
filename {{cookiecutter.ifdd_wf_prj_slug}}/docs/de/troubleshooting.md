(ifdd-wf-troubleshooting)=
# Fehlersuche
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

Beginnen mit `docker compose -f docker-compose-production.yml logs kestra`
und den Executions in der Kestra-Oberfläche.

## Start

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `adm_02_run.sh`: `.env missing` oder `secrets/kestra.env missing` | erzeugte Dateien fehlen | neu erzeugen oder aus den `.dist`-Dateien anlegen |
| `adm_02_run.sh`: `placeholders <<generate:...>> left` | ein Wert wurde nicht erzeugt | ihn von Hand setzen, mit der Qualität, die der Platzhalter nennt |
| `adm_02_run.sh`: `Docker network ... missing` | der Proxy läuft nicht | zuerst den Proxy starten |
| `adm_02_run.sh`: `runner image ... missing` | die Images wurden nicht gebaut | `./adm_01_build.sh production` |
| `adm_02_run.sh`: `SECRET_GIT_TOKEN is empty` | das Token des Inhalts-Repositorys fehlt | in `secrets/kestra.env` eintragen: `printf '%s' 'token' \| base64 -w0` |
| `adm_02_run.sh`: `restore failed ... git_push NOT loaded` | die Wiederherstellung scheiterte: Token, Branch, Repository-URL oder ein Zertifikat | die Execution von `system.git_restore` in der Oberfläche öffnen, die Ursache beheben, erneut `./adm_02_run.sh production` |
| Kestra steht minutenlang auf `starting` | Kestra lädt beim Start seine Plugins | warten; der Healthcheck lässt 120 s Zeit |
| Kestra erreicht die Datenbank nach einer Änderung an `.env` nicht | die Datenbank behält das Passwort, mit dem sie angelegt wurde | das alte `IFDD_WF_DB_PASSWORD` wiederherstellen |
| verschlüsselte Werte lassen sich nicht lesen | `IFDD_WF_ENCRYPTION_KEY` wurde geändert | den alten Schlüssel aus der Sicherung zurückholen |

## Zugang

| Symptom | Ursache | Abhilfe |
|---|---|---|
{%- if sso %}
| 403 nach der Keycloak-Anmeldung | der Benutzer ist nicht in `{{ cookiecutter.ifdd_wf_sso_group }}` oder hat keine bestätigte E-Mail-Adresse | Gruppe zuordnen; Adresse bestätigen |
| `/oauth2/callback` antwortet 404 | der Router für den Login-Callback fehlt, oder oauth2-proxy ist nicht healthy | die Router im Dashboard des Proxys prüfen |
| endlose Login-Schleife; das Proxy-Log meldet `the service "<name>@docker" does not exist` | `ifdd_proxy_oauth2_proxy_service` weicht vom Wert der Proxy-Instanz ab; Traefik verwirft den Router des Login-Callbacks | den Wert des Proxys setzen (`cruft update --variables-to-update`), Kestra neu erzeugen ({ref}`ifdd-wf-setup-several-servers`) |
{%- endif %}
| die Kestra-Anmeldung scheitert | falsche Anmeldedaten, oder Kestra unter einem Pfadpräfix | `IFDD_WF_ADMIN_USER`/`IFDD_WF_ADMIN_PASSWORD` nehmen; Kestra an der Wurzel seines Hosts ausliefern |

## Flows

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `secret('...')` ist leer oder falsch | nicht Base64 in `secrets/kestra.env`, mit Zeilenumbruch kodiert, oder Kestra nicht neu gestartet | `printf '%s' 'value' \| base64 -w0`; `./adm_02_run.sh production` |
| ein Task-Container löst einen Dienstnamen nicht auf | dem Task fehlt `networkMode: "{% raw %}{{ envs.task_network }}{% endraw %}"`, oder `ENV_TASK_NETWORK` fehlt in `secrets/kestra.env` | beides setzen |
| ein Task-Container vertraut einem Zertifikat nicht | die CA liegt nicht in `certs/`, oder das Image wurde nicht neu gebaut | kopieren, `./adm_01_build.sh production` |
| das Runner-Image wird in einem Task nicht gefunden | `pullPolicy: NEVER` und das Image ist nicht im Daemon | `./adm_02_run.sh production` lädt es |
| ein importierter Flow aus Kestra 1.x wird abgewiesen | Task-Typen haben sich in Kestra 2.0 geändert (etwa `ForEach` -> `Loop`) | den Flow anpassen; siehe den Migrationsleitfaden von Kestra für 2.0 |
| `system.git_push` scheitert | das Token ist abgelaufen oder darf nicht schreiben, der Branch fehlt, oder die Variablen `ifdd_wf_git_*` sind falsch | das Log der Execution nennt die Ursache; das Token in `secrets/kestra.env` erneuern und `./adm_02_run.sh production` |
| ein Git-Task scheitert mit `could not be established because of SSL problems` | die CA des Git-Hosts oder eines TLS-prüfenden Proxys fehlt im Java-Trust-Store von Kestra | nach `certs/` kopieren, `./adm_01_build.sh production`, `./adm_02_run.sh production` |
| ein gelöschter Kind-Namespace ist nach einem Neuaufbau wieder da | sein Ordner blieb in Git | den Ordner im Inhalts-Repository löschen |
