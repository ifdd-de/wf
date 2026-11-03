"""Check that the login callback router names the service of the proxy.

    python tests/check_sso_service.py <fixture.yaml> <rendered instance>

The router <slug>-oauth2 must name the Traefik service of oauth2-proxy that
ifdd-de/proxy declares: ifdd_proxy_oauth2_proxy_service, a variable both
templates share, plus "@docker". If the names differ, Traefik drops the
router, and the login callback passes the login again (a loop). The
deprecated ifdd_wf_sso_service still wins when it differs from its old
default "oauth2-proxy@docker".
"""

import json
import sys
from pathlib import Path

import yaml

TEMPLATE = Path(__file__).resolve().parent.parent


def main(fixture, instance):
    defaults = json.loads((TEMPLATE / "cookiecutter.json").read_text())
    context = {**defaults, **yaml.safe_load(Path(fixture).read_text())["default_context"]}
    if context["ifdd_wf_enable_sso"] != "y":
        print("SKIP  no SSO in this fixture")
        return 0
    legacy = context["ifdd_wf_sso_service"]
    expected = legacy if legacy != "oauth2-proxy@docker" else context["ifdd_proxy_oauth2_proxy_service"] + "@docker"
    compose = yaml.safe_load((Path(instance) / "docker-compose-production.yml").read_text())
    labels = compose["services"]["kestra"]["labels"]
    found = [label.split("=", 1)[1] for label in labels
             if label.startswith("traefik.http.routers.") and "-oauth2.service=" in label]
    if found != [expected]:
        print(f"FAIL  login callback router names {found}, expected [{expected!r}]")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
