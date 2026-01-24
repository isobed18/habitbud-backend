# habits/models.py

from django.db import models, transaction
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
import uuid

User = get_user_model()

class Habit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits', db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    habit_type = models.CharField(max_length=10, choices=[('time', 'Time-based'), ('count', 'Count-based')])
    
    # Hedefler
    target_count = models.IntegerField(null=True, blank=True)
    target_time = models.DurationField(null=True, blank=True)
    
    # İlerleme (Günlük)
    count = models.PositiveIntegerField(default=0)
    total_time = models.DurationField(null=True, blank=True)
    
    # İstatistikler (Cache amaçlı alanlar)
    streak = models.IntegerField(default=0, db_index=True)
    best_streak = models.IntegerField(default=0, db_index=True)
    completed_count = models.IntegerField(default=0, db_index=True)
    last_completed_date = models.DateField(null=True, blank=True, db_index=True)
    
    # Sosyal Özellikler
    verified_count = models.IntegerField(default=0, help_text="Arkadaş onaylı tamamlanma sayısı.")
    verification_streak = models.IntegerField(default=0)
    last_proof_submission_date = models.DateField(null=True, blank=True)
    
    # AI Specific
    ai_streak = models.IntegerField(default=0)
    last_ai_verification_date = models.DateField(null=True, blank=True)
    
    # Challenge Linkage
    is_challenge_habit = models.BooleanField(default=False)
    challenge = models.ForeignKey('challange.Challenge', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_habits')

    # Zamanlama
    created_at = models.DateField(auto_now_add=True, null=True, db_index=True)
    last_reset_date = models.DateField(default=timezone.now, db_index=True)
    FREQUENCY_CHOICES = [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('custom', 'Custom')]
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, db_index=True)
    
    COLOR_CHOICES = [
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('pink', 'Pink'),
        ('blue', 'Blue'),
    ]
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='blue')
    custom_frequency_days = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'last_completed_date']),
            models.Index(fields=['frequency', 'last_reset_date']),
        ]
        ordering = ['-last_completed_date']

    def is_completed_today(self):
        """Bugünkü hedefe ulaşıldı mı kontrolü."""
        if self.habit_type == 'count' and self.target_count is not None:
            return self.count >= self.target_count
        # Time-based mantığı eklenebilir
        return False

    def calculate_streak(self):
        """
        Streak hesaplamasını 'HabitCompletion' tablosundan sorgulayarak yapar.
        JSON parse etmekten çok daha performanslıdır.
        """
        # Tarihleri tersten sırala (bugünden geçmişe)
        completions = self.completions.order_by('-completed_at').values_list('completed_at', flat=True)
        
        if not completions:
            return 0

        today = timezone.now().date()
        latest_date = completions[0]
        
        # Eğer en son tamamlama dünden eskiyse streak bozulmuştur.
        # (Bugün henüz tamamlanmamış olsa bile streak devam edebilir, o yüzden 1 günden fazla fark var mı diye bakıyoruz)
        if (today - latest_date).days > 1:
            return 0

        streak = 0
        current_check_date = latest_date

        for date in completions:
            if date == current_check_date:
                streak += 1
                current_check_date -= timedelta(days=1)
            else:
                # Ardışıklık bozuldu
                break
        
        return streak

    @transaction.atomic
    def update_and_recalculate(self):
        """
        GÜNCELLENMİŞ BEYİN: Tamamlanma durumunu 'HabitCompletion' tablosuna işler.
        """
        today = timezone.now().date()
        is_now_completed = self.is_completed_today()

        # Check if completion record exists
        existing_completion = HabitCompletion.objects.filter(
            habit=self,
            completed_at=today
        ).first()

        if is_now_completed:
            # Target reached - ensure completion record exists
            if not existing_completion:
                # Create new completion record
                HabitCompletion.objects.create(
                    habit=self,
                    completed_at=today
                )
                
                # Gamification: Award XP (only on first completion of the day)
                from users.gamification import GamificationEngine
                from users.services import UserService
                
                # Estimate new streak for reward calc (since it will be updated momentarily)
                estimated_streak = self.streak + 1
                earned_xp, multiplier = GamificationEngine.calculate_habit_xp(estimated_streak)
                
                UserService.add_xp(self.user, earned_xp)
        else:
            # Target not reached - remove completion record if it exists
            if existing_completion:
                existing_completion.delete()
        
        # İstatistikleri güncelle (Cache alanları)
        # Bu işlem aggregate sorgusuyla çok hızlı yapılır
        self.streak = self.calculate_streak()
        
        # Best Streak Update
        if self.streak > self.best_streak:
            self.best_streak = self.streak
            
        self.completed_count = self.completions.count()
        
        last_completion = self.completions.order_by('-completed_at').first()
        self.last_completed_date = last_completion.completed_at if last_completion else None

        # --- NEW: Update Verification Streak ---
        if is_now_completed: # Only update verification streak if habit is considered completed today
            self.update_verification_streak()
            
            # --- CHALLENGE SYNC: Update active challenges ---
            try:
                from challange.services import ChallengeService
                ChallengeService.sync_habit_completion(self.user, self)
            except Exception as e:
                print(f"Error syncing challenge progress: {e}")

        self.save(update_fields=['streak', 'best_streak', 'completed_count', 'last_completed_date'])

    def update_verification_streak(self):
        """
        Updates the verification streak based on proof submission.
        - Idempotent: Can be called multiple times a day but only updates once.
        - Strict: Should only be called if is_completed_today() is True.
        """
        today = timezone.now().date()
        
        # Already verified today?
        if self.last_proof_submission_date == today:
            return

        if self.last_proof_submission_date:
            delta = (today - self.last_proof_submission_date).days
            if delta == 1:
                self.verification_streak += 1
            else:
                self.verification_streak = 1
        else:
            self.verification_streak = 1
            
        self.verified_count += 1
        self.last_proof_submission_date = today
        self.save(update_fields=['verification_streak', 'verified_count', 'last_proof_submission_date'])

    def update_ai_streak(self):
        """
        Updates the AI SPECIFIC verification streak.
        - Idempotent: Can be called multiple times a day but only updates once.
        - Strict: Should only be called if is_completed_today() is True.
        """
        today = timezone.now().date()
        
        # Already processed AI streak today?
        if self.last_ai_verification_date == today:
            return

        if self.last_ai_verification_date:
            delta = (today - self.last_ai_verification_date).days
            if delta == 1:
                self.ai_streak += 1
            else:
                self.ai_streak = 1
        else:
            self.ai_streak = 1
            
        self.last_ai_verification_date = today
        self.save(update_fields=['ai_streak', 'last_ai_verification_date'])

    def check_and_reset_progress(self):
        """
        Lazy evaluation for resetting progress based on frequency.
        Called when fetching habit lists.
        Respects USER TIMEZONE.
        """
        import pytz
        try:
            user_tz = pytz.timezone(self.user.timezone)
            today = timezone.now().astimezone(user_tz).date()
        except Exception:
            # Fallback to Server Time if timezone is invalid
            today = timezone.now().date()
            
        should_reset = False

        if not self.last_reset_date:
            self.last_reset_date = today
            self.save(update_fields=['last_reset_date'])
            return

        if self.frequency == 'daily':
            if today > self.last_reset_date:
                should_reset = True
        
        elif self.frequency == 'weekly':
            # Find start of current week (Monday)
            start_of_week = today - timedelta(days=today.weekday())
            if self.last_reset_date < start_of_week:
                should_reset = True
                
        elif self.frequency == 'monthly':
            if today.month != self.last_reset_date.month or today.year != self.last_reset_date.year:
                should_reset = True

        elif self.frequency == 'custom' and self.custom_frequency_days:
            if today >= self.last_reset_date + timedelta(days=self.custom_frequency_days):
                should_reset = True

        if should_reset:
            # SNAPSHOT: Save history before resetting
            try:
                HabitHistory.objects.update_or_create(
                    habit=self,
                    date=self.last_reset_date,
                    defaults={
                        'count': self.count,
                        'total_time': self.total_time
                    }
                )
            except Exception as e:
                print(f"Error saving history snapshot: {e}")

            self.count = 0
            if self.total_time:
                self.total_time = timedelta(0)
            self.last_reset_date = today
            self.save(update_fields=['count', 'total_time', 'last_reset_date'])

    def __str__(self):
        return f"{self.name} ({self.user.username})"

# --- YENİ MODEL ---
class HabitCompletion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateField(db_index=True) # Hızlı sorgu için index şart
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('habit', 'completed_at') # Bir habit aynı gün iki kere tamamlanmış sayılamaz
        ordering = ['-completed_at']

class HabitHistory(models.Model):
    """
    Stores historical daily progress regardless of completion status.
    Used for calendar view to show exact count/time for past days (e.g. 5/10).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='history')
    date = models.DateField(db_index=True)
    count = models.PositiveIntegerField(default=0)
    total_time = models.DurationField(null=True, blank=True)
    
    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']