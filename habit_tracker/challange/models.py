from django.db import models
from django.conf import settings
from habits.models import Habit
import uuid

class Item(models.Model):
    """Collectible rewards for completing challenges."""
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='items/', null=True, blank=True)
    # Optional 3D model (GLB) — e.g. generated with Hunyuan3D, served from media/.
    model_glb = models.FileField(upload_to='models/items/', null=True, blank=True)
    model_url = models.URLField(blank=True, default='', help_text="External GLB URL (alternative to uploaded file)")
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')

    # Where the item attaches on the avatar (approximate, non-rigged MVP).
    ANCHOR_CHOICES = [
        ('head', 'Head'), ('face', 'Face'), ('hand', 'Hand'),
        ('back', 'Back'), ('neck', 'Neck'), ('none', 'None'),
    ]
    anchor = models.CharField(max_length=10, choices=ANCHOR_CHOICES, default='head')
    item_scale = models.FloatField(default=1.0, help_text="Render scale of the item on the avatar")

    def __str__(self):
        return f"{self.name} ({self.rarity})"

class UserItem(models.Model):
    """Ownership of items by users."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    obtained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'item')

class ChallengeTemplate(models.Model):
    """System-defined challenge presets."""
    TYPE_CHOICES = [('SOLO', 'Solo'), ('DUO', 'Duo (Friend)')]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    predefined_habit_name = models.CharField(max_length=100, help_text="The exact habit name user must use (e.g., 'Running')")
    challenge_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='SOLO')
    duration_days = models.PositiveIntegerField(help_text="Days required to complete")
    
    # Rewards
    reward_xp = models.PositiveIntegerField(default=100)
    reward_points = models.PositiveIntegerField(default=100)
    reward_item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.challenge_type})"

class Challenge(models.Model):
    """Active participation in a challenge."""
    STATUS_CHOICES = [
        ('PENDING', 'Invitation Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Invitation Rejected'),
        ('FAILED', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(ChallengeTemplate, on_delete=models.CASCADE, related_name='participations')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_challenges')
    partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='joined_challenges')
    
    # Derived from template
    habit_name = models.CharField(max_length=100, editable=False)
    
    current_streak = models.PositiveIntegerField(default=0)
    start_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Mutual Verification tracking (Duo Only)
    creator_completed_today = models.BooleanField(default=False)
    partner_completed_today = models.BooleanField(default=False)
    creator_verified_partner = models.BooleanField(default=False)
    partner_verified_creator = models.BooleanField(default=False)

    last_update_date = models.DateField(null=True, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        # Enforce Solo vs Duo partner rules
        if self.template.challenge_type == 'SOLO' and self.partner is not None:
             raise ValidationError("Solo challenges cannot have a partner.")
        
        if self.template.challenge_type == 'DUO' and self.partner is None:
             raise ValidationError("Duo challenges must have a partner.")
        
        if self.partner == self.creator:
             raise ValidationError("You cannot be your own partner.")

    def save(self, *args, **kwargs):
        self.full_clean() # Triggers the clean() method
        if not self.habit_name:
            self.habit_name = self.template.predefined_habit_name
        # Solo challenges start ACTIVE, Duo start PENDING if they have a partner
        if self.template.challenge_type == 'DUO' and self.partner and not self.pk:
            self.status = 'PENDING'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.template.name} for {self.creator.username}"


