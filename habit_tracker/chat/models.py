# chat/models.py

from django.db import models
from django.conf import settings
from habits.models import Habit
import uuid

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    # Group chat room support. 1:1 DMs leave these defaults.
    name = models.CharField(max_length=100, blank=True, default='')
    is_group = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='room_avatars/', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.is_group:
            return f"Room: {self.name or self.id}"
        return f"Conversation {self.id}"

class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class MessageType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        PROOF = 'PROOF', 'Proof'

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    
    # Kanıt ile ilgili alanlar
    proof_image = models.ImageField(upload_to='habit_proofs/', null=True, blank=True)
    related_habit = models.ForeignKey(Habit, on_delete=models.SET_NULL, null=True, blank=True)
    verification_status = models.CharField(max_length=10, choices=VerificationStatus.choices, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories")
    habit = models.ForeignKey(Habit, on_delete=models.SET_NULL, null=True, blank=True, related_name="stories")
    image = models.ImageField(upload_to='stories/')
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            # Ensure it works even if created_at is not yet set (for new objects)
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

class StoryLike(models.Model):
    """Likes/Reactions to stories."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')
