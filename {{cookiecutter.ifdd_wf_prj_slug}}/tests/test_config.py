"""Static checks of the generated configuration (pytest tests).

They read only files of this instance and need neither Docker nor Kestra.
"""

import base64
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MODES = ("production", "development")


def load(path):
    return yaml.safe_load((ROOT / path).read_text())


def compose(mode):
    return load(f"docker-compose-{mode}.yml")


def env_file(path):
    values = {}
    for line in (ROOT / path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def labels(service):
    return {k: v for k, v in (item.split("=", 1) for item in service.get("labels", []))}


@pytest.mark.parametrize("mode", MODES)
def test_management_port_never_published(mode):
    for name, service in compose(mode)["services"].items():
        for port in service.get("ports", []):
            assert not str(port).endswith(":8081"), f"{name} publishes the management port"


def test_production_publishes_no_port():
    for name, service in compose("production")["services"].items():
        assert not service.get("ports"), f"{name} publishes ports in production"


def test_development_binds_loopback_only():
    for port in compose("development")["services"]["kestra"]["ports"]:
        assert str(port).startswith("127.0.0.1:"), port


@pytest.mark.parametrize("mode", MODES)
def test_postgres_only_on_internal_network(mode):
    data = compose(mode)
    assert data["services"]["postgres"]["networks"] == ["db"]
    assert data["networks"]["db"]["internal"] is True


@pytest.mark.parametrize("mode", MODES)
def test_docker_access(mode):
    services = compose(mode)["services"]
    volumes = services["kestra"]["volumes"]
    if "dind" in services:
        dind = services["dind"]
        assert dind["command"] == ["dockerd", "--host=unix:///dind/docker.sock"], "DinD must not listen on TCP"
        assert not dind.get("ports")
        assert "dind-socket:/dind" in volumes
        assert not any("docker.sock" in v for v in volumes), "DinD mode must not mount the host socket"
        assert (ROOT / "dind" / "Dockerfile").exists()
    else:
        assert "/var/run/docker.sock:/var/run/docker.sock" in volumes


def test_kestra_config_has_no_literal_secrets():
    config = load("kestra/application.yml")
    secrets = [
        config["datasources"]["postgres"]["password"],
        config["kestra"]["server"]["basic-auth"]["username"],
        config["kestra"]["server"]["basic-auth"]["password"],
        config["kestra"]["encryption"]["secret-key"],
    ]
    for value in secrets:
        assert re.fullmatch(r"\$\{[A-Z0-9_]+\}", value), value


@pytest.mark.parametrize("mode", MODES)
def test_kestra_gets_every_variable_the_config_needs(mode):
    needed = set(re.findall(r"\$\{([A-Z0-9_]+)\}", (ROOT / "kestra/application.yml").read_text()))
    given = set(compose(mode)["services"]["kestra"]["environment"])
    assert needed <= given, needed - given


def test_kestra_has_no_context_path():
    # Kestra 2.0.4 does not authenticate its API under a context path, and its
    # UI calls the API without the prefix, so the login fails.
    config = load("kestra/application.yml")
    assert "context-path" not in str(config.get("micronaut") or {})


@pytest.mark.parametrize("mode", MODES)
def test_url_is_the_root_of_the_host(mode):
    url = compose(mode)["services"]["kestra"]["environment"]["IFDD_WF_URL"]
    assert re.fullmatch(r"https?://[^/]+/", url), url


def test_router_has_no_path_prefix():
    lab = labels(compose("production")["services"]["kestra"])
    rule = next(v for k, v in lab.items() if k.endswith(".rule") and "oauth2" not in k)
    assert "PathPrefix" not in rule, rule


@pytest.mark.parametrize("mode", MODES)
def test_kestra_has_a_healthcheck_on_the_management_port(mode):
    check = compose(mode)["services"]["kestra"]["healthcheck"]
    # Exec form: the image has curl but no bash.
    assert check["test"][0] == "CMD"
    assert "http://localhost:8081/health" in check["test"]


def test_forward_auth_restricts_to_a_group_when_enabled():
    lab = labels(compose("production")["services"]["kestra"])
    addresses = [v for k, v in lab.items() if k.endswith("forwardauth.address")]
    if not addresses:
        pytest.skip("SSO disabled in this instance")
    assert "allowed_groups=" in addresses[0]
    router_mw = [v for k, v in lab.items() if re.fullmatch(r"traefik\.http\.routers\.[^.]+\.middlewares", k)]
    assert router_mw and router_mw[0].endswith("-sso")


def test_generated_secrets_meet_kestra_rules():
    env = env_file(".env")
    for key, value in env.items():
        assert "<<generate:" not in value, key
    password = env["IFDD_WF_ADMIN_PASSWORD"]
    # Kestra 2.0.4 (BasicAuthService): >= 8 chars, lower, upper, digit, <= 256.
    assert re.fullmatch(r"(?=.{8,256}$)(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9]).*", password)
    assert re.fullmatch(r"[a-zA-Z0-9_!#$%&'*+/=?`{|}~^.-]+@[a-zA-Z0-9.-]+", env["IFDD_WF_ADMIN_USER"])
    assert len(base64.b64decode(env["IFDD_WF_ENCRYPTION_KEY"])) == 32


def test_kestra_env_holds_only_flow_variables():
    for key, value in env_file("secrets/kestra.env").items():
        assert key.startswith(("SECRET_", "ENV_")), key
        if key.startswith("SECRET_") and value:
            base64.b64decode(value, validate=True)


def test_gitignore_protects_secrets():
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    for entry in (".env", "secrets/*", "certs/*"):
        assert entry in ignored


def test_example_flows():
    papermill = load("examples/flows/papermill_example.yml")
    task = papermill["tasks"][0]
    assert task["taskRunner"]["pullPolicy"] == "NEVER", "local runner images cannot be pulled"
    assert task["containerImage"] == "{{ envs.runner_papermill_image }}"


def test_backend_example_reaches_the_backend_and_keeps_the_secret_out():
    flow = load("examples/flows/backend_product_count.yml")
    task = flow["tasks"][0]
    assert task["taskRunner"]["pullPolicy"] == "NEVER"
    assert task["taskRunner"]["networkMode"] == "{{ envs.task_network }}"
    env = task["env"]
    assert env["IFDD_API_CLIENT_SECRET"] == "{{ secret('IFDD_API_CLIENT_SECRET') }}"
    for name in ("IFDD_BE_URL", "IFDD_OIDC_TOKEN_URL", "IFDD_API_CLIENT_ID"):
        assert env[name] == "{{ envs." + name.lower() + " }}"
    # papermill writes parameters into the executed notebook: no secret there.
    assert "secret(" not in " ".join(task["commands"])
    kestra_env = env_file("secrets/kestra.env.dist")
    for name in (
        "ENV_IFDD_BE_URL",
        "ENV_IFDD_OIDC_TOKEN_URL",
        "ENV_IFDD_API_CLIENT_ID",
        "SECRET_IFDD_API_CLIENT_SECRET",
    ):
        assert name in kestra_env, name
    assert kestra_env["SECRET_IFDD_API_CLIENT_SECRET"] == ""
    assert kestra_env["ENV_IFDD_OIDC_TOKEN_URL"].endswith("/protocol/openid-connect/token")


def test_task_network_reaches_the_proxy_network():
    """Task containers resolve https://rest and https://id only on the proxy network."""
    network = env_file("secrets/kestra.env.dist")["ENV_TASK_NETWORK"]
    production = compose("production")
    if "dind" in production["services"]:
        assert network == "host"  # the network of the dind container
        assert "proxy" in production["services"]["dind"]["networks"]
    else:
        assert network == production["networks"]["proxy"]["name"]


def test_backend_notebook_has_parameters_and_reads_the_environment():
    import json

    notebook = json.loads((ROOT / "examples/notebooks/backend_product_count.ipynb").read_text())
    cells = notebook["cells"]
    parameters = [c for c in cells if "parameters" in c["metadata"].get("tags", [])]
    assert len(parameters) == 1 and "".join(parameters[0]["source"]).startswith('segment = "products"')
    code = "".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
    for name in ("IFDD_BE_URL", "IFDD_OIDC_TOKEN_URL", "IFDD_API_CLIENT_ID", "IFDD_API_CLIENT_SECRET"):
        assert f'setting("{name}")' in code
    assert all(not c.get("outputs") for c in cells if c["cell_type"] == "code"), "commit the notebook without outputs"


# --- Git synchronisation (flows/system/, kestra/git_sync.py) ---------------

GIT_ENV = ("ENV_GIT_URL", "ENV_GIT_USERNAME", "ENV_GIT_BRANCH", "ENV_GIT_NAMESPACES")


def git_tasks(flow):
    """Every NamespaceSync/Clone task of a flow, also inside Loop and WorkingDirectory."""
    found = []

    def walk(tasks):
        for task in tasks:
            if task["type"].startswith("io.kestra.plugin.git."):
                found.append(task)
            walk(task.get("tasks", []))

    walk(flow["tasks"])
    return found


def test_git_flows_use_the_configured_repository_and_the_token():
    for name in ("git_push", "git_restore"):
        flow = load(f"flows/system/{name}.yml")
        assert flow["id"] == name and flow["namespace"] == "system"
        tasks = git_tasks(flow)
        assert tasks, name
        for task in tasks:
            assert task["url"] == "{{ envs.git_url }}"
            assert task["username"] == "{{ envs.git_username }}"
            assert task["password"] == "{{ secret('GIT_TOKEN') }}"
            assert task["branch"] == "{{ envs.git_branch }}"


def test_git_push_mirrors_kestra_without_touching_system():
    flow = load("flows/system/git_push.yml")
    assert flow["concurrency"]["limit"] == 1, "a scheduled and a manual push must not overlap"
    loop = flow["tasks"][0]
    assert loop["values"] == "{{ envs.git_namespaces | split(',') }}"
    (sync,) = git_tasks(flow)
    assert sync["type"] == "io.kestra.plugin.git.NamespaceSync"
    assert sync["sourceOfTruth"] == "KESTRA"
    assert sync["whenMissingInSource"] == "DELETE"
    assert sync["includeChildNamespaces"] is True
    assert sync["protectedNamespaces"] == ["system"]


def test_git_restore_restores_each_namespace_on_its_own():
    # The open-source edition cannot create a namespace through its API, so a
    # restore with includeChildNamespaces skips missing child namespaces.
    flow = load("flows/system/git_restore.yml")
    assert [i["id"] for i in flow["inputs"]] == ["namespace"]
    sync = next(t for t in git_tasks(flow) if t["type"] == "io.kestra.plugin.git.NamespaceSync")
    assert sync["sourceOfTruth"] == "GIT"
    assert sync["includeChildNamespaces"] is False
    assert sync["whenMissingInSource"] == "KEEP"
    assert flow["tasks"][1]["values"] == "{{ outputs.list.vars.namespaces }}"


def test_git_settings_reach_kestra_in_production_only():
    production = compose("production")["services"]["kestra"]
    for name in GIT_ENV:
        assert production["environment"][name], name
    assert "./flows/system:/etc/kestra/system-flows:ro" in production["volumes"]
    assert "./kestra/git_sync.py:/etc/kestra/git_sync.py:ro" in production["volumes"]
    development = compose("development")["services"]["kestra"]
    assert not set(GIT_ENV) & set(development["environment"])
    assert not any("system-flows" in v for v in development["volumes"])


def test_kestra_env_holds_the_git_token():
    # secrets/ is on the skip list: an updated instance keeps its old
    # kestra.env.dist, so only the entry both versions share is checked.
    assert env_file("secrets/kestra.env.dist")["SECRET_GIT_TOKEN"] == ""


def test_tasks_call_the_api_on_localhost_with_kestras_login():
    # NamespaceSync calls Kestra's API; kestra.url is the public URL behind the proxy.
    auth = load("kestra/application.yml")["kestra"]["tasks"]["sdk"]["authentication"]
    assert auth["url"] == "http://localhost:8080"
    assert auth["username"] == "${IFDD_WF_ADMIN_USER}"
    assert auth["password"] == "${IFDD_WF_ADMIN_PASSWORD}"


def test_kestra_image_trusts_certs_in_java_before_they_are_removed():
    dockerfile = (ROOT / "kestra/Dockerfile").read_text()
    java = dockerfile.index("ifdd-install-java-certs /tmp/ifdd-certs")
    system = dockerfile.index("ifdd-install-certs /tmp/ifdd-certs")
    assert java < system, "install-certs.sh removes the directory"


def test_adm_scripts_parse():
    import subprocess

    for script in ("adm_01_build.sh", "adm_02_run.sh", "adm_03_git_push.sh", "adm_99_destroy.sh"):
        path = ROOT / script
        assert path.stat().st_mode & 0o111, f"{script} is not executable"
        subprocess.run(["bash", "-n", str(path)], check=True)


def test_adm_02_refuses_production_without_token_and_sets_up_the_sync():
    script = (ROOT / "adm_02_run.sh").read_text()
    assert "^SECRET_GIT_TOKEN=.+" in script
    assert "git_sync.py bootstrap" in script


def test_destroy_pushes_first_and_needs_confirmation():
    script = (ROOT / "adm_99_destroy.sh").read_text()
    assert script.startswith("#!/usr/bin/env bash")
    assert script.index("./adm_03_git_push.sh") < script.index("down --volumes") < script.index('rm -rf -- "$DIR"')
    assert '[ "$answer" = destroy ]' in script
