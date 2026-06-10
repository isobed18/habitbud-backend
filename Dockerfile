# HabitBud backend — Django + DRF + Channels served by Daphne (ASGI).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps: libpq for psycopg2 wheels' runtime, curl for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY habit_tracker/requirements.txt .
RUN pip install -r requirements.txt

COPY habit_tracker/ .

# Static files are baked into the image (served by WhiteNoise). A throwaway
# secret is fine here — collectstatic never uses it for anything persistent.
RUN SECRET_KEY=build-only DEBUG=True python manage.py collectstatic --noinput

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fs http://localhost:8000/api/health/ || exit 1

# Run migrations, then serve HTTP + WebSockets with Daphne.
CMD ["sh", "-c", "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p 8000 habit_tracker.asgi:application"]
