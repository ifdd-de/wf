# Secrets

Git-ignored except for this file and `kestra.env.dist`.

| File | Content |
|---|---|
| `kestra.env` | flow secrets (`SECRET_*`, base64) and flow variables (`ENV_*`), created from `kestra.env.dist` at generation |

The passwords of Kestra and PostgreSQL and the encryption key are in `.env`
(generated). Back up both files together with the database: without
`IFDD_WF_ENCRYPTION_KEY` encrypted values in the database cannot be read.

After a change to `kestra.env`: `./adm_02_run.sh <mode>` (Kestra reads
`SECRET_*` only at start).
