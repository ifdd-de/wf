# Docker-in-Docker daemon for the containers that flows start (Docker task
# runner, Docker plugin). The upstream image plus the instance's CA
# certificates, so that image pulls through a TLS-inspecting proxy work.
#
# The daemon listens only on the unix socket in the volume shared with Kestra
# (see the compose files); there is no TCP port.
ARG DIND_IMAGE
FROM ${DIND_IMAGE}

COPY build/install-certs.sh /usr/local/sbin/ifdd-install-certs
COPY certs/ /tmp/ifdd-certs/
RUN sh /usr/local/sbin/ifdd-install-certs /tmp/ifdd-certs
