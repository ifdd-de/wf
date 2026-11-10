(ifdd-wf-troubleshooting)=
# Troubleshooting
{%- set sso = cookiecutter.ifdd_wf_enable_sso == "y" %}

Start with `docker compose -f docker-compose-production.yml logs kestra` and
the executions in the Kestra UI.

## Start

| Symptom | Cause | Remedy |
|---|---|---|
| `adm_02_run.sh`: `.env missing` or `secrets/kestra.env missing` | generated files are missing | regenerate, or create them from the `.dist` files |
| `adm_02_run.sh`: `placeholders <<generate:...>> left` | a value was not generated | set it by hand with the quality the placeholder names |
| `adm_02_run.sh`: `Docker network ... missing` | the proxy is not running | start the proxy first |
| `adm_02_run.sh`: `runner image ... missing` | the images were not built | `./adm_01_build.sh production` |
| `adm_02_run.sh`: `SECRET_GIT_TOKEN is empty` | the token of the content repository is missing | enter it in `secrets/kestra.env`: `printf '%s' 'token' \| base64 -w0` |
| `adm_02_run.sh`: `restore failed ... git_push NOT loaded` | the restore failed: token, branch, repository URL or a certificate | open the execution of `system.git_restore` in the UI, fix the cause, `./adm_02_run.sh production` again |
| Kestra stays `starting` for minutes | Kestra loads its plugins at start | wait; the health check allows 120 s |
| Kestra cannot connect to the database after `.env` was changed | the database keeps the password it was created with | restore the old `IFDD_WF_DB_PASSWORD` |
| encrypted values cannot be read | `IFDD_WF_ENCRYPTION_KEY` changed | restore the old key from the backup |

## Access

| Symptom | Cause | Remedy |
|---|---|---|
{%- if sso %}
| 403 after the Keycloak login | the user is not in `{{ cookiecutter.ifdd_wf_sso_group }}`, or has no verified e-mail address | add the group; verify the address |
| `/oauth2/callback` answers 404 | the router of the login callback is missing, or oauth2-proxy is not healthy | check the routers in the proxy dashboard |
| endless login loop; the proxy log says `the service "<name>@docker" does not exist` | `ifdd_proxy_oauth2_proxy_service` differs from the value of the proxy instance; Traefik drops the router of the login callback | set the proxy's value (`cruft update --variables-to-update`), recreate Kestra ({ref}`ifdd-wf-setup-several-servers`) |
{%- endif %}
| the Kestra login fails | wrong credentials, or Kestra under a path prefix | use `IFDD_WF_ADMIN_USER`/`IFDD_WF_ADMIN_PASSWORD`; serve Kestra at the root of its host |

## Flows

| Symptom | Cause | Remedy |
|---|---|---|
| `secret('...')` is empty or wrong | not base64 in `secrets/kestra.env`, encoded with a newline, or Kestra not restarted | `printf '%s' 'value' \| base64 -w0`; `./adm_02_run.sh production` |
| a task container cannot resolve a service name | the task lacks `networkMode: "{% raw %}{{ envs.task_network }}{% endraw %}"`, or `ENV_TASK_NETWORK` is missing in `secrets/kestra.env` | set both |
| a task container does not trust a certificate | the CA is not in `certs/`, or the image was not rebuilt | copy it, `./adm_01_build.sh production` |
| the runner image is not found in a task | `pullPolicy: NEVER` and the image is not in the daemon | `./adm_02_run.sh production` loads it |
| an imported flow of Kestra 1.x is refused | task types changed in Kestra 2.0 (for example `ForEach` -> `Loop`) | adapt the flow; see the Kestra migration guide for 2.0 |
| `system.git_push` fails | the token expired or may not write, the branch is missing, or the variables `ifdd_wf_git_*` are wrong | the execution log names the cause; renew the token in `secrets/kestra.env` and run `./adm_02_run.sh production` |
| a Git task fails with `could not be established because of SSL problems` | the CA of the Git host, or of a TLS-inspecting proxy, is not in the Java trust store of Kestra | copy it into `certs/`, `./adm_01_build.sh production`, `./adm_02_run.sh production` |
| a deleted child namespace is back after a rebuild | its folder stayed in Git | delete the folder in the content repository |
