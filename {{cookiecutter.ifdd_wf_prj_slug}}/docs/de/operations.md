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

`examples/flows/system_git_sync.yml` (Namespace `system`, stündlich) schiebt
die Flows und Namespace-Dateien der aufgeführten Namespaces mit
`io.kestra.plugin.git.NamespaceSync`, `sourceOfTruth: KESTRA`. Änderungen in
Git werden nicht zurückgeholt. `whenMissingInSource: KEEP` lässt in Kestra
gelöschte Flows in Git stehen; auf `DELETE` umstellen, um Löschungen zu
spiegeln.

## Änderungen übernehmen

| Geändert | Zu tun |
|---|---|
| `secrets/kestra.env` | `./adm_02_run.sh production` (Kestra liest sie beim Start) |
| `kestra/application.yml` | Kestra neu starten |
| `certs/`, `kestra/Dockerfile`, `kestra/requirements.txt`, {% if dind %}`dind/`, {% endif %}`runners/`, Image-Versionen | `./adm_01_build.sh production`, dann `./adm_02_run.sh production` |

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
von Hand nachtragen. Wer `IFDD_WF_DB_PASSWORD` nur in `.env` ändert, sperrt
Kestra aus: PostgreSQL behält das Passwort, mit dem die Datenbank angelegt
wurde.
