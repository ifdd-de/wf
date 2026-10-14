"""After generation: create .env and secrets/kestra.env with generated secrets.

dotenv.dist marks every value that must be unique per instance with a
placeholder that also states the required quality:

    <<generate:chars:LENGTH:CLASSES>>   random characters; CLASSES picks from
                                        a (a-z), A (A-Z), 0 (0-9), - (-_.+),
                                        and the result contains at least one
                                        character of every class named
    <<generate:base64:BYTES>>           BYTES random bytes, standard base64
    <<generate:hex:BYTES>>              BYTES random bytes as hex

The generator is the same for every template that needs passwords; only
dotenv.dist differs. Existing files are never touched, so running the hook
again (cruft update renders into a temporary directory) cannot replace a real
value.
"""

import base64
import os
import re
import secrets
import shutil
import string
import sys
from pathlib import Path

TERMINATOR = "\x1b[0m"
SUCCESS = "\x1b[1;32m [SUCCESS]: "

CLASSES = {
    "a": string.ascii_lowercase,
    "A": string.ascii_uppercase,
    "0": string.digits,
    # Safe in .env (no $, quotes, # or spaces), in YAML placeholders and in URLs.
    "-": "-_.+",
}
PLACEHOLDER = re.compile(r"<<generate:(chars|base64|hex):(\d+)(?::([aA0-]+))?>>")

DOCKER_MODE = "{{ cookiecutter.ifdd_wf_docker_mode }}"


def random_chars(length, classes):
    pools = [CLASSES[c] for c in dict.fromkeys(classes)]
    if length < len(pools):
        raise ValueError(f"length {length} cannot hold one character of each class {classes}")
    alphabet = "".join(pools)
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(any(ch in pool for ch in value) for pool in pools):
            return value


def generate(match):
    kind, size, classes = match.group(1), int(match.group(2)), match.group(3)
    if kind == "chars":
        return random_chars(size, classes or "aA0")
    raw = secrets.token_bytes(size)
    return base64.b64encode(raw).decode() if kind == "base64" else raw.hex()


def fill(source, target, mode=0o600):
    if target.exists():
        return False
    # Comment lines are copied as they are: they document the placeholders.
    lines = [
        line if line.lstrip().startswith("#") else PLACEHOLDER.sub(generate, line)
        for line in source.read_text().splitlines(keepends=True)
    ]
    target.write_text("".join(lines))
    target.chmod(mode)
    return True


def main():
    root = Path.cwd()
    fill(root / "dotenv.dist", root / ".env")

    secret_dir = root / "secrets"
    secret_dir.mkdir(exist_ok=True)
    fill(root / "secrets" / "kestra.env.dist", secret_dir / "kestra.env")

    if DOCKER_MODE != "dind":
        shutil.rmtree(root / "dind", ignore_errors=True)

    left = [
        p for p in (root / ".env", secret_dir / "kestra.env")
        if any("<<generate:" in line for line in p.read_text().splitlines() if not line.lstrip().startswith("#"))
    ]
    if left:
        print(f"Unresolved placeholders in {', '.join(map(str, left))}", file=sys.stderr)
        sys.exit(1)
    print(SUCCESS + "Project initialized; .env and secrets/kestra.env created." + TERMINATOR)


if __name__ == "__main__":
    main()
