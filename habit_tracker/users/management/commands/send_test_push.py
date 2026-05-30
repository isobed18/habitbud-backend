"""Fire a batch of sample push notifications for manual device testing.

Usage:
    # Send to every registered device:
    python manage.py send_test_push

    # Send to one specific Expo token:
    python manage.py send_test_push --token "ExponentPushToken[xxxxxxxx]"

    # Send to all of a user's devices:
    python manage.py send_test_push --user runner

Each run sends three messages (a check approval, a streak alert, and a
reminder) so you can confirm they all land on the phone at once.
"""
from django.core.management.base import BaseCommand

from users.push import send_push

SAMPLES = [
    ("Check'in onaylandı! 🔥", "drinker, su check'ini onayladı. +12 XP!", {"type": "CHECK"}),
    ("🔥 Su streak'in tehlikede!", "Su streak'in (7 gün) gece yarısı bitiyor. Hemen bir su check'i gönder!", {"type": "STREAK"}),
    ("⏰ Su İç", "Bugün su içtin mi? Su check'ini göndermeyi unutma 💧", {"type": "REMINDER"}),
]


class Command(BaseCommand):
    help = "Send sample push notifications to test device delivery."

    def add_arguments(self, parser):
        parser.add_argument('--token', help="A single Expo push token to send to.")
        parser.add_argument('--user', help="Username whose devices should receive the test.")

    def handle(self, *args, **options):
        tokens = []
        if options['token']:
            tokens = [options['token']]
        else:
            from users.models import DeviceToken
            qs = DeviceToken.objects.all()
            if options['user']:
                qs = qs.filter(user__username=options['user'])
            tokens = list(qs.values_list('token', flat=True))

        if not tokens:
            self.stdout.write(self.style.ERROR(
                "No tokens to send to. Register a device first (log in on a dev build) "
                "or pass --token."
            ))
            return

        self.stdout.write(f"Sending {len(SAMPLES)} test notifications to {len(tokens)} token(s)...")
        for title, body, data in SAMPLES:
            ok = send_push(tokens, title, body, data)
            self.stdout.write(("  sent: " if ok else "  FAILED: ") + title)
        self.stdout.write(self.style.SUCCESS("Done. Check your device."))
