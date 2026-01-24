# friends/models.py

from django.db import models
from django.conf import settings
import uuid

class Friendship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendship_requests_sent'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendship_requests_received'
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Friendship Streak
    streak = models.IntegerField(default=0)
    last_interaction_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def update_streak(self):
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.last_interaction_date:
            delta = (today - self.last_interaction_date).days
            if delta == 1:
                self.streak += 1
            elif delta > 1:
                self.streak = 1
            # If delta == 0 (same day), do nothing
        else:
            self.streak = 1
            
        self.last_interaction_date = today
        self.save(update_fields=['streak', 'last_interaction_date'])

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"