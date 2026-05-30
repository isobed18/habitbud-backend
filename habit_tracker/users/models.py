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