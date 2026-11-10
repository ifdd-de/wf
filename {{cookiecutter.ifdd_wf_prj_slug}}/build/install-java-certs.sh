#!/bin/sh
# Add every certificate of every *.crt / *.pem in $1 to the default trust
# store of the Java runtime (keytool -cacerts). A file may hold a bundle
# (for example an intermediate and its root CA): each certificate in it is
# imported under its own alias. Leaves $1 in place. Does nothing when there
# is no certificate.
set -eu
src=${1:?usage: install-java-certs.sh DIR}
keytool=$(command -v keytool || true)
if [ -z "$keytool" ] && [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/keytool" ]; then
    keytool=$JAVA_HOME/bin/keytool
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
found=0
for f in "$src"/*.crt "$src"/*.pem; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    name=${name%.*}
    # One file per certificate: keytool reads only the first one of a bundle.
    awk -v out="$work/$name" '
        /-----BEGIN CERTIFICATE-----/ { n++; file = out "-" n ".pem"; inside = 1 }
        inside { print > file }
        /-----END CERTIFICATE-----/ { inside = 0; close(file) }
    ' "$f"
done
for cert in "$work"/*.pem; do
    [ -f "$cert" ] || continue
    if [ -z "$keytool" ]; then
        echo "install-java-certs: keytool not found (no JDK/JRE on PATH or in JAVA_HOME)" >&2
        exit 1
    fi
    alias="ifdd-$(basename "$cert" .pem)"
    # Replace an entry of the same name, so that a rebuild on top of an
    # earlier layer does not fail. "changeit" is the documented default
    # password of the JDK trust store; it protects nothing secret.
    "$keytool" -delete -cacerts -storepass changeit -alias "$alias" >/dev/null 2>&1 || true
    if ! out=$("$keytool" -importcert -noprompt -cacerts -storepass changeit \
        -alias "$alias" -file "$cert" 2>&1); then
        echo "$out" >&2
        exit 1
    fi
    echo "install-java-certs: added $alias"
    found=$((found + 1))
done
if [ "$found" -eq 0 ]; then
    echo "install-java-certs: no certificates, Java trust store unchanged"
fi
