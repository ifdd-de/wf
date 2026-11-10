"""Load the Git synchronisation flows into Kestra, restore, push.

Runs inside the Kestra container, where adm_02_run.sh and adm_03_git_push.sh
call it with `docker compose exec`; only the Python standard library is used.
It talks to Kestra's API on localhost with Kestra's own login
(IFDD_WF_ADMIN_USER, IFDD_WF_ADMIN_PASSWORD), so neither the proxy nor the
login gate is in the way, and no secret appears on a command line.

    git_sync.py bootstrap   load system.git_restore; restore every root
                            namespace of ENV_GIT_NAMESPACES that has no flow;
                            only if all of that succeeded, load system.git_push
    git_sync.py push        run system.git_push and wait for its result

Exit code 0 on success, 1 on failure, 2 on wrong usage.
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

API = "http://localhost:8080/api/v1/main"
FLOWS = "/etc/kestra/system-flows"
NAMESPACE = "system"
FINAL = {"SUCCESS", "WARNING", "FAILED", "KILLED", "CANCELLED", "SKIPPED"}
TIMEOUT = 1800  # seconds to wait for one execution
POLL = 2


class Failure(Exception):
    pass


def say(message):
    print(f"git sync: {message}", flush=True)


class Kestra:
    def __init__(self, api, user, password):
        self.api = api.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.auth = f"Basic {token}"

    def call(self, method, path, body=None, content_type=None, missing_ok=False):
        request = urllib.request.Request(self.api + path, data=body, method=method)
        request.add_header("Authorization", self.auth)
        if content_type:
            request.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            detail = error.read().decode(errors="replace")[:500]
            raise Failure(f"{method} {path}: HTTP {error.code} {detail}") from None
        except urllib.error.URLError as error:
            raise Failure(f"{method} {path}: {error.reason}") from None
        return json.loads(raw) if raw else None

    def load_flow(self, path):
        """Create or update one flow of the namespace system; never deletes others."""
        with open(path, "rb") as source:
            self.call("POST", f"/flows/{NAMESPACE}?delete=false", source.read(), "application/x-yaml")

    def flow_count(self, namespace):
        """Flows in the namespace and its child namespaces (filter PREFIX)."""
        query = urllib.parse.urlencode({"size": 1, "filters[namespace][PREFIX]": namespace})
        return self.call("GET", f"/flows/search?{query}")["total"]

    def run(self, flow, inputs=None):
        """Start an execution of system.<flow> and wait until it ends; return (id, state)."""
        boundary = uuid.uuid4().hex
        parts = []
        for name, value in (inputs or {}).items():
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
            )
        body = ("".join(parts) + f"--{boundary}--\r\n").encode()
        execution = self.call(
            "POST", f"/executions/{NAMESPACE}/{flow}", body, f"multipart/form-data; boundary={boundary}"
        )
        execution_id = execution["id"]
        deadline = time.monotonic() + TIMEOUT
        while True:
            state = self.call("GET", f"/executions/{execution_id}")["state"]["current"]
            if state in FINAL:
                return execution_id, state
            if time.monotonic() > deadline:
                raise Failure(f"execution {execution_id} of {NAMESPACE}.{flow} still {state} after {TIMEOUT} s")
            time.sleep(POLL)


def bootstrap(kestra, flows, namespaces):
    kestra.load_flow(os.path.join(flows, "git_restore.yml"))
    say(f"loaded {NAMESPACE}.git_restore")
    failed = []
    for namespace in namespaces:
        count = kestra.flow_count(namespace)
        if count:
            say(f"{namespace}: {count} flow(s) in Kestra, nothing to restore")
            continue
        say(f"{namespace}: no flow in Kestra, restoring from Git")
        execution_id, state = kestra.run("git_restore", {"namespace": namespace})
        if state == "SUCCESS":
            say(f"{namespace}: restored, {kestra.flow_count(namespace)} flow(s) (execution {execution_id})")
        else:
            say(f"{namespace}: restore ended {state} (execution {execution_id})")
            failed.append(namespace)
    if failed:
        raise Failure(
            f"restore failed for {', '.join(failed)}; {NAMESPACE}.git_push NOT loaded, so nothing "
            f"is pushed over the repository. See the executions of {NAMESPACE}.git_restore in the UI."
        )
    kestra.load_flow(os.path.join(flows, "git_push.yml"))
    say(f"loaded {NAMESPACE}.git_push (hourly)")


def push(kestra):
    if kestra.call("GET", f"/flows/{NAMESPACE}/git_push", missing_ok=True) is None:
        raise Failure(f"{NAMESPACE}.git_push is not loaded; start with ./adm_02_run.sh production first")
    execution_id, state = kestra.run("git_push")
    if state != "SUCCESS":
        raise Failure(f"push ended {state} (execution {execution_id}); see it in the UI")
    say(f"pushed (execution {execution_id})")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["bootstrap", "push"])
    parser.add_argument("--api", default=API, help="Kestra API base (tests only)")
    parser.add_argument("--flows", default=FLOWS, help="directory of the system flows (tests only)")
    args = parser.parse_args(argv)

    missing = [n for n in ("IFDD_WF_ADMIN_USER", "IFDD_WF_ADMIN_PASSWORD", "ENV_GIT_NAMESPACES") if not os.environ.get(n)]
    if missing:
        print(f"git sync: ERROR: {', '.join(missing)} not set in the Kestra container", file=sys.stderr)
        return 1
    namespaces = [n for n in os.environ["ENV_GIT_NAMESPACES"].split(",") if n]
    kestra = Kestra(args.api, os.environ["IFDD_WF_ADMIN_USER"], os.environ["IFDD_WF_ADMIN_PASSWORD"])
    try:
        if args.command == "bootstrap":
            bootstrap(kestra, args.flows, namespaces)
        else:
            push(kestra)
    except Failure as error:
        print(f"git sync: ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
