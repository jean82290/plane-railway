"""Railway start-up tasks for the Plane API, run by start.sh before the
official API entrypoint.

    python /railway/bootstrap.py migrate        apply migrations, one process at a time
    python /railway/bootstrap.py admin          create the instance administrator once
    python /railway/bootstrap.py ensure-bucket  create the uploads bucket once storage is up
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


def ensure_bucket(timeout=3600):
    """Runs in the background so the API starts even if the storage service
    is still building; retries until the uploads bucket exists."""
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    endpoint = os.environ.get("AWS_S3_ENDPOINT_URL", "")
    bucket = os.environ.get("AWS_S3_BUCKET_NAME", "uploads")
    parsed = urlparse(endpoint)
    if not parsed.hostname:
        log("AWS_S3_ENDPOINT_URL is not set, not creating the uploads bucket")
        return
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION") or "us-east-1",
        config=boto3.session.Config(signature_version="s3v4"),
    )
    deadline = time.monotonic() + timeout
    delay = 5
    while True:
        try:
            socket.create_connection((parsed.hostname, port), timeout=5).close()
            try:
                client.head_bucket(Bucket=bucket)
                log(f"bucket '{bucket}' ready")
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") not in ("404", "NoSuchBucket", "NotFound"):
                    raise
                client.create_bucket(Bucket=bucket)
                log(f"bucket '{bucket}' created")
            return
        except (OSError, BotoCoreError, ClientError) as error:
            if time.monotonic() > deadline:
                log(f"gave up creating bucket '{bucket}': {error}")
                return
            log(f"storage not ready yet, retrying in {delay}s ({error})")
            time.sleep(delay)
            delay = min(delay * 2, 60)


COMMANDS = {
    "migrate": migrate,
    "admin": create_admin,
    "ensure-bucket": ensure_bucket,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(f"usage: bootstrap.py {{{'|'.join(COMMANDS)}}}")
    COMMANDS[sys.argv[1]]()
