"""Smart, habit-aware reminder dispatcher.

Run this on a schedule (cron / Windows Task Scheduler), e.g. hourly:

    python manage.py send_check_reminders

It does two things, both de-duplicated to once per day:

1. Due reminders — any active Reminder whose scheduled hour matches "now"
   fires a notification (+ push). Habit-linked reminders use the template copy
   like "Don't forget to send your water check today 💧".

2. Streak-at-risk warnings — in the evening, any habit with a live verification
   streak that has NOT received a check today gets a "your streak will break"
   nudge so users come back and send a check.

Replaces the old `process_reminders` command (which had a duplicate-send bug).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import Reminder, Notification
from users.notifications import notify

# Only send streak-risk nudges from this local hour onwards (give people the day).
STREAK_RISK_HOUR = 18


class Command(BaseCommand):
    help = "Dispatch due habit reminders and streak-at-risk nudges (run hourly)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Print what would be sent without sending.")

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.localtime()
        today = now.date()

        sent_reminders = self._dispatch_due_reminders(now, today, dry_run)
        sent_risks = self._dispatch_streak_risks(now, today, dry_run)

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Reminders sent: {sent_reminders}, streak nudges: {sent_risks}."
        ))

    def _dispatch_due_reminders(self, now, today, dry_run):
        due = Reminder.objects.filter(
            is_active=True,
            time__hour=now.hour,
        ).exclude(last_sent_date=today).select_related('user', 'habit')

        count = 0
        for reminder in due:
            count += 1
            if dry_run:
                self.stdout.write(f"  reminder → {reminder.user.username}: {reminder.message}")
                continue
            notify(
                reminder.user,
                reminder.title or "⏰ Reminder",
                reminder.message,
                ntype='REMINDER',
                data={'habit_id': str(reminder.habit_id) if reminder.habit_id else None},
            )
            reminder.last_sent_date = today
            reminder.save(update_fields=['last_sent_date'])
        return count

    def _dispatch_streak_risks(self, now, today, dry_run):
        if now.hour < STREAK_RISK_HOUR:
            return 0

        from habits.models import Habit

        at_risk = Habit.objects.filter(
            verification_streak__gte=1,
        ).exclude(last_proof_submission_date=today).select_related('user')

        count = 0
        for habit in at_risk:
            # De-dupe: one streak nudge per habit per day.
            already = Notification.objects.filter(
                user=habit.user,
                notification_type='STREAK',
                created_at__date=today,
                title__icontains=habit.name,
            ).exists()
            if already:
                continue

            count += 1
            msg = (f"Your {habit.name} streak ({habit.verification_streak} days) ends at midnight. "
                   f"Send a {habit.name} check now to keep it alive! 🔥")
            if dry_run:
                self.stdout.write(f"  streak-risk → {habit.user.username}: {msg}")
                continue
            notify(
                habit.user,
                f"🔥 {habit.name} streak at risk!",
                msg,
                ntype='STREAK',
                data={'habit_id': str(habit.id), 'streak': habit.verification_streak},
            )
        return count
