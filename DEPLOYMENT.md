# HabitBud Backend — Deployment Guide

Django 5 + DRF + Channels (WebSockets), served by **Daphne** (ASGI). Static files
via WhiteNoise; media from local disk (`/media/`). SQLite for dev, **Postgres**
for production via `DATABASE_URL`; **Redis** for the Channels layer.

## Option A — Docker (recommended)

```bash
cp habit_tracker/.env.example .env
# edit .env: set SECRET_KEY (required), ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS,
# CSRF_TRUSTED_ORIGINS, POSTGRES_PASSWORD
docker compose up -d --build
curl http://localhost:8000/api/health/   # -> {"status": "ok"}
```

The compose stack runs **web (Daphne) + Postgres 16 + Redis 7**, auto-migrates on
boot, persists DB + media in volumes. Put nginx/Caddy with TLS in front and point
it at port 8000 (WebSockets need `Upgrade`/`Connection` headers proxied).

## Option B — Bare server

```bash
cd habit_tracker
python -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in values; set DEBUG=False
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/daphne -b 0.0.0.0 -p 8000 habit_tracker.asgi:application
```

Run Daphne under systemd/supervisor. Redis is required when running more than
one process (the InMemory channel layer is single-process only).

## Environment variables

| Var | Required in prod | Notes |
|---|---|---|
| `SECRET_KEY` | **yes** — boot fails on the placeholder | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` | enables HSTS, secure cookies, SSL redirect |
| `ALLOWED_HOSTS` | yes | comma-separated domains |
| `DATABASE_URL` | recommended | `postgres://user:pass@host:5432/db` (SQLite fallback) |
| `REDIS_URL` | for WebSockets at scale | `redis://host:6379/0` (InMemory fallback) |
| `CORS_ALLOWED_ORIGINS` | yes | comma-separated frontend origins |
| `CSRF_TRUSTED_ORIGINS` | for admin over HTTPS | `https://api.example.com` |
| `SECURE_SSL_REDIRECT` | `False` behind a TLS-terminating proxy | default `True` |
| `THROTTLE_ANON` / `THROTTLE_USER` | optional | default `60/min` / `300/min` |
| `EXPO_ACCESS_TOKEN` | optional | only if Expo enhanced push security is on |

## Scheduled jobs (cron / Task Scheduler)

No Celery — plain management commands:

```cron
*/15 * * * *  cd /app && python manage.py process_reminders
0 18 * * *    cd /app && python manage.py send_check_reminders
```

## Initial content

```bash
python manage.py seed_habit_templates
python manage.py import_avatar_models --dir <socketed glbs> --thumbs-dir <2d pngs> --replace
python manage.py import_items --dir <item glbs> --thumbs-dir <2d pngs>
python manage.py import_combos --dir <combo glbs>
```

## Frontend pairing

Set the deployed API URL when building the app (see frontend `eas.json` /
`app.json > expo.extra.apiUrl`), e.g. `https://api.example.com/`. WebSockets use
the same host (`ws(s)://.../ws/chat/...`).

## Pre-flight checklist

- [ ] `DEBUG=False`, real `SECRET_KEY`, correct `ALLOWED_HOSTS`
- [ ] `python manage.py check --deploy` → 0 issues
- [ ] `python manage.py makemigrations --check --dry-run` → no pending changes
- [ ] Postgres + Redis reachable; `/api/health/` returns ok
- [ ] TLS in front; `CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` set
- [ ] Cron jobs installed; media volume backed up
