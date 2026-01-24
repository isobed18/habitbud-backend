from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Reminder, Notification

class Command(BaseCommand):
    help = 'Process recurring reminders and create notifications if due.'

    def handle(self, *args, **kwargs):
        # In a real system, this runs every minute via Celery Beat or Cron.
        # It checks if current_time.minute == reminder.time.minute (roughly)
        
        now = timezone.now().time()
        # Tolerance window (e.g. within this minute)
        # For demo purposes, we can't easily match exact seconds, so we match HH:MM
        
        # Simple match: Reminders scheduled for THIS HH:MM
        # Warning: If run multiple times in a minute, duplicates occur. 
        # Needs last_sent_at tracking in production.
        
        reminders = Reminder.objects.filter(is_active=True, time__hour=now.hour, time__minute=now.minute)
        
        count = 0
        for reminder in reminders:
            # Create Notification
            Notification.objects.create(
                user=reminder.user,
                title=f"⏰ {reminder.title}",
                message=reminder.message,
                notification_type='INFO'
            )
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f'Processed reminders. Sent {count} notifications.'))
