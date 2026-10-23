#!/bin/bash
# Starts one Plane backend process on Railway. PLANE_ROLE picks which one:
#   api     Django API (runs migrations and first-boot setup before starting)
#   worker  Celery worker
#   beat    Celery beat scheduler
set -euo pipefail
cd /code

role="${PLANE_ROLE:-api}"
echo "plane-railway: starting '${role}' (Plane ${PLANE_VERSION:-unknown})"

case "$role" in
  api)
    python manage.py wait_for_db
    # Migrations run here, under a database lock, instead of in a separate
    # migrator container that would sit stopped in the Railway canvas.
    python /railway/bootstrap.py migrate
    python manage.py register_instance railway
    python manage.py configure_instance
    # Creates the instance administrator from ADMIN_EMAIL / ADMIN_PASSWORD so
    # the first visitor of /god-mode/ cannot claim the instance.
    python /railway/bootstrap.py admin
    # The official entrypoint creates the uploads bucket; make sure the
    # storage service is reachable first.
    python /railway/bootstrap.py wait-storage
    exec ./bin/docker-entrypoint-api.sh
    ;;
  worker)
    python manage.py wait_for_db
    python manage.py wait_for_migrations
    # Celery would otherwise start one process per CPU of the Railway host.
    exec celery -A plane worker -l info --concurrency "${CELERY_WORKER_CONCURRENCY:-2}"
    ;;
  beat)
    exec ./bin/docker-entrypoint-beat.sh
    ;;
  *)
    echo "plane-railway: unknown PLANE_ROLE '${role}', expected api, worker or beat" >&2
    exit 1
    ;;
esac
