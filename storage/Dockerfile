# S3-compatible storage for Plane uploads: Silo, the maintained MinIO fork
# that Plane's own Docker Compose setup uses. Private to the project; the
# Plane proxy forwards signed upload and download requests to it.
ARG SILO_VERSION=RELEASE.2026-09-16T00-00-00Z
FROM pgsty/silo:${SILO_VERSION}

ENV MINIO_BROWSER=off

CMD ["server", "/data", "--address", ":9000"]
