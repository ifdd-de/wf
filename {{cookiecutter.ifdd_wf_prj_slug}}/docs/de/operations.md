(ifdd-wf-operations)=
# Betrieb
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}

## Starten, Stoppen, Reihenfolge

```bash
./adm_02_run.sh production       # Prüfungen, {% if dind %}lädt die Runner-Images in DinD, {% endif %}docker compose up -d
docker compose -f docker-compose-production.yml ps
docker compose -f docker-compose-production.yml down     # behält die Volumes
```

`adm_02_run.sh` startet nicht ohne `.env`, ohne `secrets/kestra.env`, mit
übrig gebliebenen Platzhaltern `<<generate:...>>`, ohne das Proxy-Netz
(Produktion) oder ohne das Runner-Image. Kestra wartet auf eine gesunde
Datenbank{% if dind %} und einen gesunden Docker-in-Docker-Daemon{% endif %}.
Beim Herunterfahren wartet es bis zu fünf Minuten auf laufende Tasks
(`stop_grace_period: 6m`). Nach Proxy, Keycloak und Backend starten
(`.adm_03_up_services.sh` des Meta-Repositorys tut das).

## Healthchecks

| Container | Prüfung | Intervall |
|---|---|---|
| `kestra` | `curl` auf `http://localhost:8081/health` (Management-Port, nicht veröffentlicht) | 15 s, Timeout 5 s, 5 Versuche, Startphase 120 s |
| `postgres` | `pg_isready -d kestra -U kestra` | 10 s, 10 Versuche |
{%- if dind %}
| `dind` | `docker info` | 10 s, 12 Versuche |
{%- endif %}

Alle Container starten mit `restart: always` neu.

## Logs

```bash
docker compose -f docker-compose-production.yml logs -f kestra
```

Die Logs von Flows und Tasks stehen in der Kestra-Oberfläche (Executions).

## Task-Container
{%- if dind %}

Container, die Flows starten, laufen im Dienst `dind`: ein privilegierter
Docker-Daemon, der nur auf `/dind/docker.sock` in einem mit Kestra geteilten
Volume lauscht. Der Docker-Task-Runner von Kestra nutzt diesen Socket, wenn
`/var/run/docker.sock` nicht existiert. Der Daemon hat einen eigenen
Image-Speicher: Die lokalen Runner-Images lädt `adm_02_run.sh`; alles andere
zieht der Daemon, mit den CAs aus `certs/`.

In Produktion hängt der Container `dind` auch in
`{{ cookiecutter.ifdd_proxy_network }}`. Ein Task mit
`networkMode: "{% raw %}{{ envs.task_network }}{% endraw %}"` (`host`, aus
`secrets/kestra.env`) teilt dieses Netz und erreicht andere Dienste über
ihre Namen, über die Netz-Aliasse des Proxys. Ohne das können Task-Container
Dienstnamen nicht auflösen.
{%- else %}

Container, die Flows starten, laufen im Docker-Daemon des Hosts
(`/var/run/docker.sock` in Kestra eingebunden). Ein Task, der andere Dienste
über ihren Namen aufruft, setzt
`networkMode: "{% raw %}{{ envs.task_network }}{% endraw %}"`
(`{{ cookiecutter.ifdd_proxy_network }}`, aus `secrets/kestra.env`).
{%- endif %}

Flows binden nur dann Volumes in Task-Container ein, wenn
`ifdd_wf_docker_volume_enabled=y` ist (hier
`{{ cookiecutter.ifdd_wf_docker_volume_enabled }}`); die Pfade beziehen sich
dann auf {% if dind %}den Docker-in-Docker-Container{% else %}den Host{% endif %}.

```{note}
Nicht getestet: der Docker-Task-Runner, `networkMode` und die Namensauflösung
aus Task-Containern{% if dind %} im Docker-in-Docker-Daemon{% endif %}.
```

## Git-Synchronisation

In Produktion hält Kestra die Flows und Namespace-Dateien (etwa Notebooks)
der Wurzel-Namespaces `{{ cookiecutter.ifdd_wf_git_namespaces }}` und ihrer Kind-Namespaces im
Inhalts-Repository `{{ cookiecutter.ifdd_wf_git_url }}`, Branch `{{ cookiecutter.ifdd_wf_git_branch }}`. Aufbau in Git:
`<namespace>/flows/<flow>.yaml` und `<namespace>/files/<pfad>`. Die beiden
Flows des Namespace `system`, die die Arbeit tun, kommen aus `flows/system/`
der Instanz, nicht aus Git; `adm_02_run.sh` lädt sie bei jedem Start, Änderungen
in der Oberfläche bleiben also nicht.

### Push (Kestra nach Git)

`system.git_push` läuft stündlich; `./adm_03_git_push.sh` startet ihn sofort
und wartet auf das Ergebnis. Kestra ist die Quelle der Wahrheit: Ein in Kestra
gelöschter Flow oder eine gelöschte Datei wird auch in Git gelöscht und
bleibt in dessen Historie. Änderungen in Git überschreibt der nächste Push;
nach Kestra kommen sie nur durch einen Neuaufbau. Zwei Pushes laufen nie
gleichzeitig.

### Restore (Git nach Kestra)

`./adm_02_run.sh production` prüft nach dem Start jeden Wurzel-Namespace. Ein
Wurzel-Namespace ohne einen einzigen Flow in Kestra, seine Kind-Namespaces
eingeschlossen, wird von `system.git_restore` aus Git wiederhergestellt; die
übrigen bleiben unberührt. Nur wenn jede Wiederherstellung gelang, wird
`system.git_push` geladen. Sonst endet das Skript mit einem Fehler, Kestra
läuft weiter und nichts wird geschoben; eine neue, leere Instanz kann das
Repository also nicht überschreiben. Der Restore listet die
Namespace-Ordner in Git und stellt jeden einzeln wieder her: Die
Open-Source-Edition kann über ihre API keinen Namespace anlegen.

`kestra/git_sync.py` erledigt das im Kestra-Container über Kestras API auf
`localhost`, mit der Kestra-Anmeldung aus `.env`. Die Git-Tasks rufen Kestras
API ebenso auf (`kestra.tasks.sdk.authentication` in
`kestra/application.yml`), nicht über die öffentliche URL hinter dem Proxy.

### Löschen und neu aufbauen

```bash
./adm_99_destroy.sh     # fragt nach "destroy"
```

Das Skript schiebt ein letztes Mal und bricht ab, wenn das scheitert. Dann
entfernt es die Container, alle Volumes, die lokal gebauten Images und das
Instanzverzeichnis mit `.env` und `secrets/`. Zum Neuaufbau die Instanz neu
erzeugen ({ref}`ifdd-wf-setup`), `SECRET_GIT_TOKEN` und die übrigen Secrets in
`secrets/kestra.env` eintragen, dann `./adm_01_build.sh production` und
`./adm_02_run.sh production`: Die Flows und Namespace-Dateien kommen aus Git
zurück. Executions und ihre Logs, der KV-Store, Secrets außerhalb von
`secrets/kestra.env` und Flow-Entwürfe (sie werden nie geschoben) kommen
nicht zurück.

### Grenzen

Beobachtet mit Kestra 2.0.8 und plugin-git 4.6.3:

- Ein Kind-Namespace mit Namespace-Dateien, aber ohne Flow, wird nicht
  geschoben. Solche Dateien in einem Namespace mit Flow ablegen, etwa in der
  Wurzel.
- Wird der letzte Flow eines Kind-Namespace gelöscht, verschwindet der
  Namespace aus Kestra, sein Ordner bleibt aber in Git, und ein Neuaufbau
  holt ihn zurück. Den Ordner im Repository von Hand löschen.
- Ein Neuaufbau stellt den Stand des Branches wieder her; was nicht
  geschoben war, ist verloren.

```{note}
Nicht getestet: die Synchronisation in den Containern dieser Instanz
(Images, Netze, ein TLS-prüfender Proxy). Getestet wurde mit dem
Release-Binary von Kestra 2.0.8 und plugin-git 4.6.3 gegen lokale
Repositorys, eines davon hinter HTTPS mit eigener CA.
```

## Änderungen übernehmen

| Geändert | Zu tun |
|---|---|
| `secrets/kestra.env` | `./adm_02_run.sh production` (Kestra liest sie beim Start) |
| `kestra/application.yml` | Kestra neu starten |
| `flows/system/`, `kestra/git_sync.py` | `./adm_02_run.sh production` (lädt die Flows neu) |
| `certs/`, `build/`, `kestra/Dockerfile`, `kestra/requirements.txt`, {% if dind %}`dind/`, {% endif %}`runners/`, Image-Versionen | `./adm_01_build.sh production`, dann `./adm_02_run.sh production` |

## Sicherung

`.env`, `secrets/kestra.env` und die Volumes `postgres-data` und
`kestra-storage` gemeinsam sichern. Ohne `IFDD_WF_ENCRYPTION_KEY` lassen sich
die verschlüsselten Werte in der Datenbank nicht lesen. Die Flows liegen
zusätzlich im Inhalts-Repository (Git-Synchronisation).

```{note}
Nicht getestet: Sicherung und Wiederherstellung.
```

## Aktualisieren

Template-Updates kommen mit `cruft update --skip .env --skip secrets --skip
certs`. `secrets/kestra.env` wird nur einmal geschrieben: Einträge, die eine
neue Template-Version in `kestra.env.dist` ergänzt (etwa `ENV_TASK_NETWORK`),
von Hand nachtragen. Eine Template-Variable, die eine neue Template-Version
ergänzt (etwa `ifdd_wf_git_url`), bekommt in einer bestehenden Instanz die
Vorgabe des Templates; mit `cruft update --variables-to-update` setzen.
Wer `IFDD_WF_DB_PASSWORD` nur in `.env` ändert, sperrt
Kestra aus: PostgreSQL behält das Passwort, mit dem die Datenbank angelegt
wurde.
