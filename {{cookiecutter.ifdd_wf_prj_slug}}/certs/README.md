# Additional CA certificates

Place the PEM files of internal CAs here (`*.crt` or `*.pem`, one certificate
per file). They are git-ignored; the meta repository copies them in after the
cruft run (`copy_wf_certs.sh`).

At build time they are added to the system trust store of

- the Kestra image (for Python processes of the Process task runner; Kestra's
  JVM keeps its own trust store and does not use them),
- the Docker-in-Docker image (for image pulls through a TLS-inspecting proxy),
- the papermill runner image.

`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE` and `PIP_CERT` point to the system
bundle in the Kestra and the runner image. Without files here the images keep
their default trust store. Rebuild after a change: `./adm_01_build.sh <mode>`.
