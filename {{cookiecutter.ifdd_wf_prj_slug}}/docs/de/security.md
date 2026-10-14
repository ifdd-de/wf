(ifdd-wf-security)=
# Sicherheit
{%- set dind = cookiecutter.ifdd_wf_docker_mode == "dind" %}
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

Wer Flows bearbeiten kann, kann Code in Containern mit Docker-Zugriff
ausführen. Zugang zu Kestra wie administrativen Zugang zum Host behandeln.

## Zugang

{% if sso -%}
- Der Router schickt jede Anfrage durch das Login-Gate des Proxys
  (forwardAuth an oauth2-proxy mit `allowed_groups={{ cookiecutter.ifdd_wf_sso_group }}`):
  Browser ohne Sitzung werden zu Keycloak geschickt, angemeldete Benutzer
  außerhalb der Gruppe bekommen 403.
- Die eigene Anmeldung von Kestra (Basic Authentication,
  `IFDD_WF_ADMIN_USER`) bleibt als zweiter Faktor; alle Mitglieder der Gruppe
  teilen sich dieses eine Kestra-Konto.
{%- else -%}
- In dieser Instanz steht kein Login-Gate vor Kestra
  (`ifdd_wf_enable_sso`); die eigene Anmeldung von Kestra (Basic
  Authentication, `IFDD_WF_ADMIN_USER`) ist der einzige Schutz. Alle, die
  sie kennen, teilen sich ein Kestra-Konto.
{%- endif %}
- Kestra wird an der Wurzel eines eigenen Hostnamens ausgeliefert, nie unter
  einem Pfadpräfix: Kestra 2.0.4 authentifiziert seine API unter einem
  Kontextpfad nicht, und seine Oberfläche ruft die API dann ohne das Präfix
  auf, sodass die Anmeldung scheitert.

## Docker-Zugriff

{% if dind -%}
Task-Container laufen in einem privilegierten Docker-in-Docker-Container. Er
ist root auf dem Kernel des Hosts, hält aber den eigenen Docker-Daemon des
Hosts außer Reichweite. Der Daemon lauscht nur auf einem Unix-Socket in
einem mit Kestra geteilten Volume, nicht auf TCP. Der Container `dind` hängt
in `{{ cookiecutter.ifdd_proxy_network }}`: Task-Container mit
`networkMode: host` erreichen jeden Dienst in diesem Netz, wie jeder
Container dort.
{%- else -%}
Der Docker-Socket des Hosts ist in Kestra eingebunden. Das gibt Kestra und
jedem Flow root-gleiche Kontrolle über den Host.
{%- endif %} Kestra selbst läuft als root (nötig für den Docker-Socket).

## Secrets

- `.env` enthält die Anmeldung von Kestra, das Datenbankpasswort und den
  Verschlüsselungsschlüssel; `secrets/kestra.env` die Flow-Secrets und
  -Variablen. Beide sind von Git ausgenommen und stehen auf der empfohlenen
  Skip-Liste.
- Jede Variable in `secrets/kestra.env` sieht jeder Flow und jeder Prozess,
  den der Process-Task-Runner startet.
- Der Client `{{ cookiecutter.ifdd_keycloak_api_client_id }}` darf nur
  lesen. Sein Secret erreicht ein Notebook als Umgebungsvariable, nie als
  papermill-Parameter: Parameter werden in das ausgeführte Notebook
  geschrieben.
- Das Git-Token sollte nur Schreibrecht auf das Inhalts-Repository haben.

## Netz und Ports

Der Management-Port 8081 (Health, Metriken) hat keine Authentifizierung und
wird nie veröffentlicht. PostgreSQL hängt nur im internen Netz `db`. In
Produktion ist kein Port veröffentlicht; Kestra ist nur über den Proxy
erreichbar.
