"""kestra/git_sync.py against a stand-in of Kestra's API (no Kestra needed).

The stand-in answers only the calls git_sync.py makes and records them, so the
tests can check the order that protects the content repository: restore first,
and load the push only when every restore succeeded.
"""

import base64
import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parent.parent
USER, PASSWORD = "admin@example.org", "Secret1234abcd"
PREFIX = "/api/v1/main"


class FakeKestra:
    def __init__(self, flows=None, results=None):
        self.flows = dict(flows or {})  # namespace -> number of flows
        self.results = dict(results or {})  # flow id or namespace -> final state
        self.loaded = []  # ids of flows loaded into the namespace system
        self.restored = []  # namespaces passed to git_restore
        self.pushes = 0
        self.executions = {}


def handler(kestra):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body=None):
            data = json.dumps(body).encode() if body is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authorised(self):
            expected = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
            if self.headers.get("Authorization") != expected:
                self.reply(401)
                return False
            return True

        def do_GET(self):
            if not self.authorised():
                return
            url = urlparse(self.path)
            path = url.path.removeprefix(PREFIX)
            if path == "/flows/search":
                namespace = parse_qs(url.query)["filters[namespace][PREFIX]"][0]
                self.reply(200, {"total": kestra.flows.get(namespace, 0), "results": []})
            elif path.startswith("/executions/"):
                self.reply(200, {"state": {"current": kestra.executions[path.rsplit("/", 1)[1]]}})
            elif path == "/flows/system/git_push":
                self.reply(200, {"id": "git_push"}) if "git_push" in kestra.loaded else self.reply(404)
            else:
                self.reply(404)

        def do_POST(self):
            if not self.authorised():
                return
            url = urlparse(self.path)
            path = url.path.removeprefix(PREFIX)
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
            if path == "/flows/system":
                assert parse_qs(url.query)["delete"] == ["false"], "loading must never delete flows"
                assert self.headers["Content-Type"] == "application/x-yaml"
                kestra.loaded.append(re.search(r"^id: (\S+)", body, re.M).group(1))
                self.reply(200, [])
            elif path == "/executions/system/git_restore":
                namespace = re.search(r'name="namespace"\r\n\r\n([^\r]*)\r\n', body).group(1)
                kestra.restored.append(namespace)
                execution = f"restore-{namespace}"
                state = kestra.results.get(namespace, "SUCCESS")
                kestra.executions[execution] = state
                if state == "SUCCESS":
                    kestra.flows[namespace] = 1
                self.reply(200, {"id": execution})
            elif path == "/executions/system/git_push":
                kestra.pushes += 1
                kestra.executions["push"] = kestra.results.get("git_push", "SUCCESS")
                self.reply(200, {"id": "push"})
            else:
                self.reply(404)

    return Handler


@pytest.fixture
def api():
    servers = []

    def start(kestra):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(kestra))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_port}{PREFIX}"

    yield start
    for server in servers:
        server.shutdown()


def git_sync(api_url, command, namespaces="ifdd,acme"):
    env = dict(
        os.environ,
        IFDD_WF_ADMIN_USER=USER,
        IFDD_WF_ADMIN_PASSWORD=PASSWORD,
        ENV_GIT_NAMESPACES=namespaces,
    )
    return subprocess.run(
        [sys.executable, str(ROOT / "kestra/git_sync.py"), command, "--api", api_url, "--flows", str(ROOT / "flows/system")],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_bootstrap_restores_only_empty_namespaces_then_loads_the_push(api):
    kestra = FakeKestra(flows={"acme": 3})
    result = git_sync(api(kestra), "bootstrap")
    assert result.returncode == 0, result.stderr
    assert kestra.restored == ["ifdd"]
    assert kestra.loaded == ["git_restore", "git_push"]


def test_bootstrap_of_a_running_instance_restores_nothing(api):
    kestra = FakeKestra(flows={"ifdd": 2, "acme": 1})
    result = git_sync(api(kestra), "bootstrap")
    assert result.returncode == 0, result.stderr
    assert kestra.restored == []
    assert kestra.loaded == ["git_restore", "git_push"]


@pytest.mark.parametrize("state", ["FAILED", "KILLED", "WARNING"])
def test_failed_restore_never_loads_the_push(api, state):
    kestra = FakeKestra(results={"ifdd": state})
    result = git_sync(api(kestra), "bootstrap")
    assert result.returncode == 1
    assert kestra.restored == ["ifdd", "acme"], "the other namespaces are still restored"
    assert "git_push" not in kestra.loaded
    assert "NOT loaded" in result.stderr


def test_push_waits_for_the_result(api):
    kestra = FakeKestra()
    kestra.loaded.append("git_push")
    assert git_sync(api(kestra), "push").returncode == 0
    kestra.results["git_push"] = "FAILED"
    result = git_sync(api(kestra), "push")
    assert result.returncode == 1 and "FAILED" in result.stderr
    assert kestra.pushes == 2


def test_push_refuses_when_the_push_flow_is_not_loaded(api):
    kestra = FakeKestra()
    result = git_sync(api(kestra), "push")
    assert result.returncode == 1 and "not loaded" in result.stderr
    assert kestra.pushes == 0


def test_wrong_login_fails(api):
    kestra = FakeKestra()
    url = api(kestra)
    env = dict(os.environ, IFDD_WF_ADMIN_USER=USER, IFDD_WF_ADMIN_PASSWORD="wrong", ENV_GIT_NAMESPACES="ifdd")
    result = subprocess.run(
        [sys.executable, str(ROOT / "kestra/git_sync.py"), "bootstrap", "--api", url, "--flows", str(ROOT / "flows/system")],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 1 and "HTTP 401" in result.stderr
    assert kestra.loaded == []
