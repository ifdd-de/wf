# Additional CA certificates

Place the PEM files of internal CAs here (`*.crt` or `*.pem`), for example
the CA of the IFDD proxy and the CAs of a TLS-inspecting proxy in front of the
Git host. They are git-ignored; the meta repository copies them in after the
cruft run (`copy_wf_certs.sh`).

At build time they are added to

- the trust store of the Java runtime of the Kestra image (Git
  synchronisation and every other HTTPS call of Kestra), each certificate of a
  file on its own, so a file may hold a bundle (`build/install-java-certs.sh`),
- the system trust store of the Kestra image (for Python processes of the
  Process task runner),
- the Docker-in-Docker image (for image pulls through a TLS-inspecting proxy),
- the papermill runner image.

`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE` and `PIP_CERT` point to the system
bundle in the Kestra and the runner image. Without files here the images keep
their default trust store. Rebuild after a change: `./adm_01_build.sh <mode>`.
