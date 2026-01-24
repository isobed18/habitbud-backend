from django.db import models
from django.contrib.auth import get_user_model
from challange.models import Challenge
import uuid

class Achievement(models.Model):
    """Specific milestones reached by users."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='achievements')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='achievement_icons/', null=True, blank=True)
    date_awarded = models.DateTimeField(auto_now_add=True)
    
    # Optional: Link to a challenge that triggered this
    challenge = models.ForeignKey(Challenge, on_delete=models.SET_NULL, null=True, blank=True, related_name='achievements')
    
    def __str__(self):
        return f"{self.name} for {self.user.username}"


