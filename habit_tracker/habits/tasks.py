# habits/tasks.py
# Celery task removed — habit reset is handled by lazy evaluation
# (check_and_reset_progress) which runs when habits are fetched via API.
# This respects user timezones and requires zero infrastructure.