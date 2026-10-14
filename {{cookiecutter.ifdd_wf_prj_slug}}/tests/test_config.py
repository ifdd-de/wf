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
    sync = load("examples/flows/system_git_sync.yml")
    inner = sync["tasks"][0]["tasks"][0]
    assert inner["sourceOfTruth"] == "KESTRA"
    assert inner["password"] == "{{ secret('GIT_TOKEN') }}"


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
