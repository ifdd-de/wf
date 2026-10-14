(ifdd-wf-notebooks)=
# Notebooks

## Papermill

`examples/flows/papermill_example.yml` führt ein Notebook aus den
Namespace-Dateien im Image `{% raw %}{{ envs.runner_papermill_image }}{% endraw %}`
(`IFDD_WF_RUNNER_PAPERMILL_IMAGE` in `.env`) mit `pullPolicy: NEVER` aus. Die
Parameterzelle des Notebooks muss den Tag `parameters` tragen. Pakete für
Notebooks gehören in das Runner-Image (siehe die Kommentare in
`runners/papermill/Dockerfile`, dann neu bauen).

## Backend-Beispiel

`examples/flows/backend_product_count.yml` führt
`examples/notebooks/backend_product_count.ipynb` aus, das das Backend fragt,
wie viele Dokumente einer Sammlung (Eingabe `segment`, Vorgabe `products`)
jetzt gültig sind (Header `X-Total-Count`), und `count.json` schreibt. Eine
Demo, kein Muster für jedes Notebook.

1. `secrets/kestra.env`: `ENV_IFDD_BE_URL`, `ENV_IFDD_OIDC_TOKEN_URL` und
   `ENV_IFDD_API_CLIENT_ID` werden beim Erzeugen gesetzt; das Secret dieses
   Clients (`IFDD_KEYCLOAK_API_CLIENT_SECRET` der Keycloak-Instanz)
   Base64-kodiert in `SECRET_IFDD_API_CLIENT_SECRET` eintragen (das
   `.adm_01_create_services.sh` des Meta-Repositorys tut das). Instanzen, die
   vor diesen Zeilen erzeugt wurden, brauchen sie von Hand, ebenso
   `ENV_TASK_NETWORK`.
2. `./adm_02_run.sh production` (Kestra liest `secrets/kestra.env` beim
   Start).
3. Das Notebook in der Oberfläche hochladen (Namespaces -> `ifdd.examples` ->
   Files) als `notebooks/backend_product_count.ipynb`, den Flow importieren,
   ausführen. `executed.ipynb` und `count.json` sind Ausgabedateien des
   Tasks.

Nur in Produktion: In der Entwicklung hängen weder Kestra noch die
Task-Container im Proxy-Netz. Der Client darf nur lesen; sein Secret
erreicht den Task als Umgebungsvariable, nie als papermill-Parameter.

## Ein Notebook außerhalb von Kestra ausführen

Das Notebook läuft auch auf einem Arbeitsplatz, der die Dienstnamen
auflöst, etwa aus dem Meta-Repository, mit installiertem `papermill`,
`ipykernel` und `requests`:

```bash
export IFDD_BE_URL={{ cookiecutter.ifdd_be_url }}
export IFDD_OIDC_TOKEN_URL={{ cookiecutter.ifdd_oidc_realm }}/protocol/openid-connect/token
export IFDD_API_CLIENT_ID={{ cookiecutter.ifdd_keycloak_api_client_id }}
export IFDD_API_CLIENT_SECRET=$(sed -n 's/^IFDD_KEYCLOAK_API_CLIENT_SECRET=//p' keycloak/.env)
export REQUESTS_CA_BUNDLE=$PWD/proxy/certs/ca.crt   # with the local CA
papermill {{ cookiecutter.ifdd_wf_prj_slug }}/examples/notebooks/backend_product_count.ipynb /tmp/executed.ipynb
```

`REQUESTS_CA_BUNDLE` ist nötig, weil `requests` sein eigenes CA-Bundle
(certifi) nutzt, nicht die CAs, denen das Betriebssystem vertraut.
