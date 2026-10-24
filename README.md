# Plane on Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/plane-1)

One-click Railway template for [Plane](https://github.com/makeplane/plane) Community Edition, the open-source project management tool (an alternative to Jira, Linear and Asana): work items, cycles, modules, pages, intake and published views.

This repository wraps the **official, unmodified** Plane images with what Railway needs to run them. It is a community template and is not affiliated with Plane Software, Inc.

## What the template does for you

| Problem with Plane's Docker setup on Railway | What this template does |
|---|---|
| The first visitor of `/god-mode/` becomes instance administrator | Creates your administrator on first boot from `ADMIN_EMAIL`, with a generated password |
| Anyone who finds the URL can sign up and create a workspace | Sign-ups are off by default (`ENABLE_SIGNUP=0`): only people you invite can join |
| Docker Compose service names (`api`, `web`…) don't exist on Railway | The proxy routes to each service's Railway private domain |
| Floating `stable` / `latest` tags change under you | Every image is pinned; one variable, `PLANE_VERSION`, upgrades all Plane services together |
| Celery starts one process per CPU of the host, which inflates memory and cost | Worker concurrency capped with `CELERY_WORKER_CONCURRENCY` (2 by default) |
| Migrations need a separate one-shot container | The API runs them on start, under a database lock |
| Object storage exposed on its own public domain | Storage stays private; signed uploads go through Plane's domain |
| Default credentials in `variables.env` | Every secret and password is generated at deploy time |

## Services

| Service | Image | Role |
|---|---|---|
| Plane | `makeplane/plane-proxy` | Public entry point (Caddy), the only service with a domain |
| Plane Web | `makeplane/plane-frontend` | Main web app |
| Plane Space | `makeplane/plane-space` | Published projects and pages, under `/spaces/` |
| Plane Admin | `makeplane/plane-admin` | Instance settings ("God mode"), under `/god-mode/` |
| Plane Live | `makeplane/plane-live` | Real-time collaborative editing, under `/live/` |
| Plane API | `makeplane/plane-backend` | Django API, migrations and first-boot setup |
| Plane Worker | `makeplane/plane-backend` | Celery worker (notifications, imports, exports, webhooks) |
| Plane Beat | `makeplane/plane-backend` | Celery scheduler |
| Postgres | Railway PostgreSQL | Main database |
| Redis | Railway Redis | Cache and real-time sync |
| RabbitMQ | `rabbitmq:3.13.6-management-alpine` | Task queue |
| Storage | `pgsty/silo` (maintained MinIO fork) | Uploaded files and attachments |

Plane services are built from this repository: each Dockerfile is a pinned `FROM` of the official image, plus start-up scripts for the backend and a Railway-aware Caddyfile for the proxy.

## Deploy

1. Click **Deploy on Railway** and enter the email address you want to sign in with.
2. Wait for every service to turn green (about five minutes the first time; the API runs Plane's database migrations).
3. Open the public URL of the **Plane** service and sign in with that email and the `ADMIN_PASSWORD` value from the **Plane API** service's **Variables** tab.
4. Create your workspace, then invite your team from the workspace settings.

The same account manages the instance at `/god-mode/`: email (SMTP), Google or GitHub sign-in, AI features, and whether people can sign up without an invitation.

## Variables

Set on the **Plane API** service; the other services reference them.

| Variable | Default | Purpose |
|---|---|---|
| `ADMIN_EMAIL` | *(you provide it)* | Email of the instance administrator created on first boot |
| `ADMIN_PASSWORD` | generated | That administrator's password. Only used on first boot |
| `ADMIN_NAME` | `Admin` | Administrator's first name |
| `PLANE_VERSION` | `v1.4.2` | Official image tag for every Plane service |
| `ENABLE_SIGNUP` | `0` | `1` lets anyone sign up; `0` admits invited people only. Only read on first boot; change it later in God mode |
| `SECRET_KEY` | generated | Django secret key. Don't change it once set |
| `LIVE_SERVER_SECRET_KEY` | generated | Shared secret between the API and the live server |
| `WEB_URL` | `https://<Plane domain>` | Public URL of the instance |
| `FILE_SIZE_LIMIT` | `5242880` | Maximum upload size, in bytes |
| `GUNICORN_WORKERS` | `1` | API processes |
| `CELERY_WORKER_CONCURRENCY` | `2` | Worker processes (set on **Plane Worker**) |

Database, Redis, RabbitMQ and storage credentials are generated and wired with Railway reference variables.

## Cost

Measured on an idle deployment, the twelve services use about 1.3 GB of RAM in total, roughly $13 a month of Railway usage. Expect $15 to $25 a month for a small team using it every day. The Hobby plan's $5 of included usage counts towards that.

## Updating Plane

Set `PLANE_VERSION` on **Plane API** to a newer tag from [Plane's releases](https://github.com/makeplane/plane/releases), then redeploy the Plane services. Migrations run automatically when the API starts.

## Custom domain

Add the domain under **Settings → Networking** of the **Plane** service, then set `WEB_URL` and `CORS_ALLOWED_ORIGINS` on **Plane API** to `https://your.domain` and redeploy.

## Email

Plane sends invitations and notifications by email once SMTP is configured in God mode. Railway only allows outbound SMTP on the Pro plan; without it, invited people can still join by signing up with the invited email address.

## Licence

Plane is © Plane Software, Inc., released under the GNU Affero General Public License v3.0. The files in this repository are released under the same licence (see `LICENSE`).
