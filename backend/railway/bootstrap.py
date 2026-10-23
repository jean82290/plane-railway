"""Railway start-up tasks for the Plane API, run by start.sh before the
official API entrypoint.

    python /railway/bootstrap.py migrate       apply migrations, one process at a time
    python /railway/bootstrap.py admin         create the instance administrator once
    python /railway/bootstrap.py wait-storage  wait for the object storage service
"""

import os
import socket
import sys
import time
import uuid
from urllib.parse import urlparse

sys.path.insert(0, "/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.production")

# Any constant works; it only has to be the same in every API replica.
MIGRATION_LOCK_ID = 7_261_611_002


def log(message):
    print(f"plane-railway: {message}", flush=True)


def setup_django():
    import django

    django.setup()


def migrate():
    setup_django()
    from django.core.management import call_command
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [MIGRATION_LOCK_ID])
    try:
        call_command("migrate", interactive=False)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_ID])


def create_admin():
    """Does what the /god-mode/ setup form does, from the template variables."""
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        log("ADMIN_EMAIL or ADMIN_PASSWORD is empty, no administrator created; set it up at /god-mode/")
        return

    setup_django()
    from django.contrib.auth.hashers import make_password
    from django.core.validators import validate_email
    from django.db import transaction
    from django.utils import timezone
    from plane.db.models import Profile, User
    from plane.license.models import Instance, InstanceAdmin

    if InstanceAdmin.objects.exists():
        log("instance administrator already set up")
        return

    validate_email(email)
    first_name = os.environ.get("ADMIN_NAME", "").strip() or "Admin"

    with transaction.atomic():
        instance = Instance.objects.select_for_update().first()
        if instance is None:
            raise SystemExit("plane-railway: the instance is not registered yet")
        if instance.is_setup_done or InstanceAdmin.objects.exists():
            log("instance administrator already set up")
            return

        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create(
                first_name=first_name,
                last_name="",
                email=email,
                username=uuid.uuid4().hex,
                password=make_password(password),
                is_password_autoset=False,
            )
            Profile.objects.create(user=user, company_name="")
            now = timezone.now()
            user.is_active = True
            user.last_active = now
            user.token_updated_at = now
            user.save()
            created = True
        else:
            created = False

        InstanceAdmin.objects.create(user=user, instance=instance)
        instance.is_setup_done = True
        instance.instance_name = os.environ.get("INSTANCE_NAME", "").strip() or "Plane"
        instance.is_telemetry_enabled = False
        instance.save()

    if created:
        log(f"instance administrator {email} created")
    else:
        log(f"existing user {email} made instance administrator, password unchanged")


def wait_for_storage(timeout=300):
    endpoint = os.environ.get("AWS_S3_ENDPOINT_URL", "")
    parsed = urlparse(endpoint)
    if not parsed.hostname:
        log("AWS_S3_ENDPOINT_URL is not set, not waiting for storage")
        return
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    deadline = time.monotonic() + timeout
    while True:
        try:
            socket.create_connection((parsed.hostname, port), timeout=5).close()
            log(f"storage reachable at {parsed.hostname}:{port}")
            return
        except OSError as error:
            if time.monotonic() > deadline:
                raise SystemExit(f"plane-railway: storage {parsed.hostname}:{port} unreachable: {error}")
            log(f"waiting for storage at {parsed.hostname}:{port} ({error})")
            time.sleep(3)


COMMANDS = {
    "migrate": migrate,
    "admin": create_admin,
    "wait-storage": wait_for_storage,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(f"usage: bootstrap.py {{{'|'.join(COMMANDS)}}}")
    COMMANDS[sys.argv[1]]()
