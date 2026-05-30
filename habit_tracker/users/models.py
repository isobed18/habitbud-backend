from django.db import models
import uuid
# Create your models here.
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    bio = models.TextField(max_length=500, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    # JSON config for a generated/dress-up avatar (style, seed, equipped items).
    # Stored as a JSON string; empty means "use uploaded avatar or letter".
    avatar_config = models.TextField(blank=True, default='')
    groups = models.ManyToManyField('groups.Group', related_name='user_groups')
    
    # Gamification
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    points = models.PositiveIntegerField(default=0)
    streak_freezes = models.PositiveIntegerField(default=0)
    
    # Settings
    timezone = models.CharField(max_length=50, default='Europe/Istanbul')
    region = models.CharField(max_length=80, blank=True, default='', help_text="Country/city for regional leaderboards")

    # Privacy (Instagram/Snapchat-style)
    MESSAGE_PRIVACY_CHOICES = [
        ('everyone', 'Everyone'),
        ('friends', 'Friends only'),
        ('nobody', 'Nobody'),
    ]
    is_private = models.BooleanField(default=False, help_text="Private profiles hide habits/stats from non-friends")
    message_privacy = models.CharField(max_length=10, choices=MESSAGE_PRIVACY_CHOICES, default='everyone')

    def __str__(self):
        return self.username

    def check_and_apply_streak_freeze(self):
        import pytz
        from django.utils import timezone
        from datetime import timedelta
        from habits.models import Habit, HabitCompletion
        from users.notifications import notify

        try:
            user_tz = pytz.timezone(self.timezone)
            local_now = timezone.now().astimezone(user_tz)
        except Exception:
            local_now = timezone.now()
            
        local_today = local_now.date()
        local_yesterday = local_today - timedelta(days=1)

        # If already frozen for yesterday, don't freeze again
        if StreakFreezeUsage.objects.filter(user=self, date=local_yesterday).exists():
            return

        # Check if they have any daily habits
        daily_habits = Habit.objects.filter(user=self, frequency='daily')
        if not daily_habits.exists():
            return

        # Did they miss completing any of their daily habits yesterday?
        has_missed_habit = False
        for habit in daily_habits:
            # Check if completed yesterday
            completed_yesterday = HabitCompletion.objects.filter(habit=habit, completed_at=local_yesterday).exists()
            if not completed_yesterday:
                has_missed_habit = True
                break

        if has_missed_habit:
            if self.streak_freezes > 0:
                self.streak_freezes -= 1
                self.save(update_fields=['streak_freezes'])
                
                StreakFreezeUsage.objects.create(user=self, date=local_yesterday)
                
                # Recalculate streaks for all daily habits to update their cached values
                for habit in daily_habits:
                    habit.streak = habit.calculate_streak()
                    if habit.streak > habit.best_streak:
                        habit.best_streak = habit.streak
                    habit.verification_streak = habit.calculate_verification_streak()
                    habit.save(update_fields=['streak', 'best_streak', 'verification_streak'])

                notify(
                    self,
                    "Seri Dondurucu Kullanıldı! ❄️",
                    "Dün bir check-in yapmayı kaçırdın ama Seri Dondurucu serini korudu!",
                    ntype='STREAK'
                )


class Block(models.Model):
    """A user blocking another. Blocked users cannot message or friend you."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('INFO', 'Info'),
        ('SUCCESS', 'Success'),
        ('WARNING', 'Warning'),
        ('CHECK', 'Check'),          # a friend approved / sent you a check
        ('STREAK', 'Streak'),        # streak milestone or streak-at-risk
        ('REMINDER', 'Reminder'),    # per-habit reminder to send a check
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='INFO')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class Reminder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reminders')
    # Optional link to a specific habit, so reminders can be habit-aware
    # ("Don't forget to send your water check today 💧").
    habit = models.ForeignKey('habits.Habit', on_delete=models.CASCADE, null=True, blank=True, related_name='reminders')
    title = models.CharField(max_length=200)
    message = models.TextField()
    time = models.TimeField()
    is_active = models.BooleanField(default=True)
    last_sent_date = models.DateField(null=True, blank=True)  # de-dupe: only fire once per day
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reminder for {self.user.username} at {self.time}"


class AvatarModel(models.Model):
    """A 3D avatar base character (GLB), e.g. a Hunyuan3D-generated plush animal.
    Served from media/ and listed for the in-app Avatar Studio (3D mode)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=80)
    emoji = models.CharField(max_length=8, blank=True, default='')
    glb = models.FileField(upload_to='models/avatars/', null=True, blank=True)
    glb_url = models.URLField(blank=True, default='', help_text="External GLB URL (alternative to uploaded file)")
    thumbnail = models.ImageField(upload_to='models/avatar_thumbs/', null=True, blank=True)
    scale = models.FloatField(default=1.0, help_text="Render scale hint for the RN viewer")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.emoji} {self.name}".strip()


class DeviceToken(models.Model):
    """An Expo push token registered by a user's device."""
    PLATFORM_CHOICES = [('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='android')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} · {self.platform} · {self.token[:20]}…"


class StreakFreezeUsage(models.Model):
    """Tracks which days a user froze their streak."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='streak_freeze_usages')
    date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} froze {self.date}"