#!/bin/sh
# Add every *.crt / *.pem in $1 to the system trust store (Debian/Ubuntu and
# Alpine), then remove $1. Does nothing when there is no certificate.
set -eu
src=${1:?usage: install-certs.sh DIR}
found=0
for f in "$src"/*.crt "$src"/*.pem; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    mkdir -p /usr/local/share/ca-certificates
    cp "$f" "/usr/local/share/ca-certificates/ifdd-${name%.*}.crt"
    found=$((found + 1))
done
rm -rf "$src"
if [ "$found" -eq 0 ]; then
    echo "install-certs: no certificates, trust store unchanged"
    exit 0
fi
if ! command -v update-ca-certificates >/dev/null 2>&1; then
    if command -v apk >/dev/null 2>&1; then
        apk add --no-cache ca-certificates
    elif command -v apt-get >/dev/null 2>&1; then
        apt-get update && apt-get install -y --no-install-recommends ca-certificates
        rm -rf /var/lib/apt/lists/*
    else
        echo "install-certs: update-ca-certificates not available" >&2
        exit 1
    fi
fi
update-ca-certificates
echo "install-certs: $found certificate(s) added"
