# habits/models.py

import logging
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
    
    # Targets
    target_count = models.IntegerField(null=True, blank=True)
    target_time = models.DurationField(null=True, blank=True)
    
    # Daily progress (reset by lazy eval)
    count = models.PositiveIntegerField(default=0)
    total_time = models.DurationField(null=True, blank=True)
    
    # Stats (cached fields — recomputed on changes)
    streak = models.IntegerField(default=0, db_index=True)
    best_streak = models.IntegerField(default=0, db_index=True)
    completed_count = models.IntegerField(default=0, db_index=True)
    last_completed_date = models.DateField(null=True, blank=True, db_index=True)
    
    # Social verification
    verified_count = models.IntegerField(default=0, help_text="Friend-verified completion count.")
    verification_streak = models.IntegerField(default=0, help_text="Consecutive days of friend-verified completions.")
    last_proof_submission_date = models.DateField(null=True, blank=True)

    # Challenge Linkage
    is_challenge_habit = models.BooleanField(default=False)
    challenge = models.ForeignKey('challange.Challenge', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_habits')

    # Timing
    created_at = models.DateField(auto_now_add=True, null=True, db_index=True)
    last_reset_date = models.DateField(default=timezone.now, db_index=True)
    FREQUENCY_CHOICES = [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('custom', 'Custom')]
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, db_index=True)
    SCHEDULE_CHOICES = [
        ('daily', 'Daily'),
        ('specific_weekdays', 'Specific weekdays'),
        ('weekly_count', 'Times per week'),
        ('monthly_count', 'Times per month'),
    ]
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default='daily')
    schedule_weekdays = models.CharField(max_length=20, blank=True, default='', help_text='Comma-separated weekday numbers, Monday=0.')
    schedule_target_count = models.PositiveSmallIntegerField(default=1)
    schedule_locked = models.BooleanField(default=False)
    
    COLOR_CHOICES = [
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('pink', 'Pink'),
        ('blue', 'Blue'),
    ]
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='blue')
    icon = models.CharField(max_length=8, blank=True, default='', help_text="Emoji shown for this habit, e.g. 💧")
    custom_frequency_days = models.IntegerField(null=True, blank=True)

    def lock_schedule_if_needed(self):
        if not self.schedule_locked and (self.completions.exists() or self.verifications.exists() or self.has_progress_today()):
            self.schedule_locked = True
            self.save(update_fields=['schedule_locked'])

    def is_due_on(self, day):
        if self.schedule_type == 'specific_weekdays':
            if not self.schedule_weekdays:
                return True
            try:
                days = {int(x) for x in self.schedule_weekdays.split(',') if x != ''}
            except ValueError:
                return True
            return day.weekday() in days
        return True

    class Meta:
        indexes = [
            models.Index(fields=['user', 'last_completed_date']),
            models.Index(fields=['frequency', 'last_reset_date']),
        ]
        ordering = ['-last_completed_date']

    def is_completed_today(self):
        """Check if today's target has been reached."""
        if self.habit_type == 'count' and self.target_count is not None:
            return self.count >= self.target_count
        if self.habit_type == 'time' and self.target_time is not None:
            return (self.total_time or timedelta(0)) >= self.target_time
        return False

    def has_progress_today(self):
        """Check whether there is any progress today, even if target is unfinished."""
        if self.habit_type == 'count':
            return self.count > 0
        if self.habit_type == 'time':
            return bool(self.total_time and self.total_time > timedelta(0))
        return False

    @property
    def streak_tier(self):
        """Returns (tier_number, tier_name) for the verification streak."""
        from users.gamification import GamificationEngine
        return GamificationEngine.get_streak_tier(self.verification_streak)

    def calculate_streak(self):
        """
        Compute completion streak dynamically from HabitCompletion records.
        Frequency-aware: daily = 1 day gap, weekly = 7 day gap, etc.
        Supports Streak Freeze mechanic for daily habits.
        """
        if self.schedule_type in ('weekly_count', 'monthly_count'):
            return self._calculate_period_streak()

        if self.frequency != 'daily':
            return self._calculate_streak_legacy()
        
        from users.models import StreakFreezeUsage
        from datetime import timedelta
        
        completions = set(self.completions.values_list('completed_at', flat=True))
        freezes = set(StreakFreezeUsage.objects.filter(user=self.user).values_list('date', flat=True))
        
        today = timezone.now().date()
        
        if not completions:
            return 0
            
        streak = 0
        current_date = today
        
        # If today has no completion and is not frozen, we start checking from yesterday.
        if today not in completions and today not in freezes:
            current_date = today - timedelta(days=1)
            
        while True:
            if current_date in completions:
                streak += 1
            elif current_date in freezes:
                # Frozen day preserves the streak but doesn't increment
                pass
            elif not self.is_due_on(current_date):
                pass
            else:
                break
            current_date -= timedelta(days=1)
            
        return streak

    def _calculate_period_streak(self):
        completions = set(self.completions.values_list('completed_at', flat=True))
        if not completions:
            return 0

        today = timezone.now().date()
        target = max(1, self.schedule_target_count or 1)
        streak = 0

        if self.schedule_type == 'weekly_count':
            period_start = today - timedelta(days=today.weekday())
            step = timedelta(days=7)
            period_days = 7
        else:
            period_start = today.replace(day=1)
            step = None
            period_days = None

        while True:
            if self.schedule_type == 'weekly_count':
                start = period_start
                end = start + timedelta(days=period_days - 1)
                count = sum(1 for d in completions if start <= d <= end)
                previous = start - step
                period_start = previous
            else:
                start = period_start
                if start.month == 12:
                    next_month = start.replace(year=start.year + 1, month=1)
                else:
                    next_month = start.replace(month=start.month + 1)
                end = next_month - timedelta(days=1)
                count = sum(1 for d in completions if start <= d <= end)
                previous_month_end = start - timedelta(days=1)
                period_start = previous_month_end.replace(day=1)

            is_current_period = start <= today <= end
            if count >= target:
                streak += 1
            elif is_current_period:
                pass
            else:
                break

            if start < min(completions):
                break

        return streak

    def _calculate_streak_legacy(self):
        from datetime import timedelta
        completions = self.completions.order_by('-completed_at').values_list('completed_at', flat=True)
        
        if not completions:
            return 0

        today = timezone.now().date()
        latest_date = completions[0]
        
        max_gap = self._get_frequency_gap_days()
        
        if (today - latest_date).days > max_gap:
            return 0

        streak = 0
        current_check_date = latest_date

        for comp_date in completions:
            gap = (current_check_date - comp_date).days
            if gap == 0:
                streak += 1
                current_check_date = comp_date - timedelta(days=1)
            elif gap <= max_gap:
                streak += 1
                current_check_date = comp_date - timedelta(days=1)
            else:
                break
        
        return streak

    def calculate_verification_streak(self):
        """
        Compute verification streak dynamically from verified proof records.
        This is the REAL streak that matters for scoring.
        Checks consecutive days where this habit was verified by a friend.
        Supports Streak Freeze mechanic.
        """
        from users.models import StreakFreezeUsage
        from datetime import timedelta
        
        verifications = set(self.verifications.values_list('verified_date', flat=True))
        freezes = set(StreakFreezeUsage.objects.filter(user=self.user).values_list('date', flat=True))
        
        today = timezone.now().date()
        
        if not verifications:
            return 0
        
        streak = 0
        current_date = today
        
        # If not verified today and not frozen today, we start checking from yesterday.
        if today not in verifications and today not in freezes:
            current_date = today - timedelta(days=1)
        
        while True:
            if current_date in verifications:
                streak += 1
            elif current_date in freezes:
                # Frozen day preserves the streak but doesn't increment
                pass
            else:
                break
            current_date -= timedelta(days=1)
        
        return streak

    def _get_frequency_gap_days(self):
        """Max allowed gap between completions before streak breaks."""
        if self.frequency == 'daily':
            return 1
        elif self.frequency == 'weekly':
            return 7
        elif self.frequency == 'monthly':
            return 31
        elif self.frequency == 'custom' and self.custom_frequency_days:
            return self.custom_frequency_days
        return 1

    @transaction.atomic
    def update_and_recalculate(self):
        """
        Handle habit completion: create/remove completion records, award flat XP.
        Streaks and multiplied XP are handled by the verification flow only.
        """
        today = timezone.now().date()
        is_now_completed = self.is_completed_today()

        existing_completion = HabitCompletion.objects.filter(
            habit=self,
            completed_at=today
        ).first()

        if is_now_completed:
            if not existing_completion:
                HabitCompletion.objects.create(
                    habit=self,
                    completed_at=today
                )
                
                # Self-completion: flat XP, no multiplier
                from users.gamification import GamificationEngine
                from users.services import UserService
                UserService.add_xp(self.user, GamificationEngine.BASE_SELF_XP)
        else:
            if existing_completion:
                existing_completion.delete()
        
        # Recompute cached stats
        self.streak = self.calculate_streak()
        if self.streak > self.best_streak:
            self.best_streak = self.streak
            
        self.completed_count = self.completions.count()
        
        last_completion = self.completions.order_by('-completed_at').first()
        self.last_completed_date = last_completion.completed_at if last_completion else None

        # Sync challenge progress
        if is_now_completed:
            try:
                from challange.services import ChallengeService
                ChallengeService.sync_habit_completion(self.user, self)
            except Exception as e:
                logging.getLogger(__name__).error(f"Error syncing challenge progress: {e}")

        self.save(update_fields=['streak', 'best_streak', 'completed_count', 'last_completed_date'])

    def update_verification_streak(self):
        """
        Called ONLY from proof verification flow (VerifyProofView).
        Records that this habit was verified today and updates streak.
        """
        today = timezone.now().date()
        
        if self.last_proof_submission_date == today:
            return  # Already verified today

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
        
        # Also create a HabitVerification record for dynamic streak calculation
        HabitVerification.objects.get_or_create(
            habit=self,
            verified_date=today,
        )
        
        self.save(update_fields=['verification_streak', 'verified_count', 'last_proof_submission_date'])

    def check_and_reset_progress(self):
        """
        Lazy evaluation for resetting daily progress based on frequency.
        Called when fetching habit lists. Respects user timezone.
        Streaks are NOT reset here — they are computed dynamically.
        """
        import pytz
        try:
            user_tz = pytz.timezone(self.user.timezone)
            today = timezone.now().astimezone(user_tz).date()
        except Exception:
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
            # Save history snapshot before resetting
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
                logging.getLogger(__name__).error(f"Error saving history snapshot: {e}")

            self.count = 0
            if self.total_time:
                self.total_time = timedelta(0)
            self.last_reset_date = today
            self.save(update_fields=['count', 'total_time', 'last_reset_date'])

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class HabitCompletion(models.Model):
    """Records that a habit's daily target was met on a given date."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('habit', 'completed_at')
        ordering = ['-completed_at']


class HabitVerification(models.Model):
    """Records that a habit was verified by a friend on a given date.
    Used for dynamic verification streak calculation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='verifications')
    verified_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('habit', 'verified_date')
        ordering = ['-verified_date']


class HabitHistory(models.Model):
    """Stores historical daily progress for calendar view."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='history')
    date = models.DateField(db_index=True)
    count = models.PositiveIntegerField(default=0)
    total_time = models.DurationField(null=True, blank=True)
    
    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']


class HabitTemplate(models.Model):
    """A predefined habit users can add with one tap (Walk, Water, Sport, ...).

    Powers the "preset library" and supplies habit-specific reminder copy
    (e.g. "Don't forget to send your water check today 💧").
    """
    CATEGORY_CHOICES = [
        ('health', 'Health'),
        ('fitness', 'Fitness'),
        ('mind', 'Mind'),
        ('productivity', 'Productivity'),
        ('lifestyle', 'Lifestyle'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=8, default='✅', help_text="Emoji, e.g. 💧")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='lifestyle')
    color = models.CharField(max_length=10, choices=Habit.COLOR_CHOICES, default='blue')

    habit_type = models.CharField(max_length=10, choices=[('time', 'Time-based'), ('count', 'Count-based')], default='count')
    default_target_count = models.IntegerField(null=True, blank=True, default=1)
    default_frequency = models.CharField(max_length=10, choices=Habit.FREQUENCY_CHOICES, default='daily')

    # Habit-specific reminder line used by smart notifications.
    reminder_copy = models.CharField(max_length=200, default="Don't forget your check today!")
    # Suggested daily reminder time (used when auto-creating a reminder).
    reminder_time = models.TimeField(null=True, blank=True)

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class HabitConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_as_user2')
    habit1 = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='connections_as_habit1')
    habit2 = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='connections_as_habit2', null=True, blank=True)
    habit_name = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='pending')
    
    streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)
    last_reset_date = models.DateField(default=timezone.now)
    
    user1_verified_today = models.BooleanField(default=False)
    user2_verified_today = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Streak Recovery
    pre_recovery_streak = models.IntegerField(default=0)
    recovery_eligible_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('habit1', 'user2')

    def check_and_reset_progress(self):
        import pytz
        try:
            user_tz = pytz.timezone(self.user1.timezone)
            today = timezone.now().astimezone(user_tz).date()
        except Exception:
            today = timezone.now().date()
            
        import datetime
        last_reset = self.last_reset_date
        if isinstance(last_reset, datetime.datetime):
            last_reset = last_reset.date()
            
        if today > last_reset:
            yesterday_date = last_reset
            # Check if yesterday was completed
            completed_yesterday = self.user1_verified_today and self.user2_verified_today
            
            # Find the conversation
            from chat.models import Conversation, ChatMessage
            from django.db.models import Count
            conversation = Conversation.objects.annotate(p_count=Count('participants')).filter(
                participants=self.user1
            ).filter(
                participants=self.user2
            ).filter(
                p_count=2, is_group=False
            ).first()

            if not completed_yesterday and self.status == 'accepted':
                # Try saving using reserves
                reserve = None
                if conversation:
                    reserve = GroupReserve.objects.filter(conversation=conversation, used=False).first()
                
                if reserve:
                    reserve.used = True
                    reserve.can_withdraw = False
                    reserve.save(update_fields=['used', 'can_withdraw'])
                    
                    RoomFreezeUsage.objects.create(conversation=conversation, date=yesterday_date)
                    
                    if conversation:
                        ChatMessage.objects.create(
                            conversation=conversation,
                            sender=None,
                            content="Streak automatically saved via Group Reserve",
                            message_type=ChatMessage.MessageType.TEXT
                        )
                else:
                    # Streak breaks reactively
                    if self.streak > 0:
                        self.pre_recovery_streak = self.streak
                        self.streak = 0
                        self.recovery_eligible_date = yesterday_date
                        
                        if conversation:
                            ChatMessage.objects.create(
                                conversation=conversation,
                                sender=None,
                                content="Streak in danger! Use a freeze to recover it.",
                                message_type=ChatMessage.MessageType.TEXT
                            )
                        
                        # Notify users
                        from users.notifications import notify
                        for u in [self.user1, self.user2]:
                            notify(u, "Serin Tehlikede! ❄️", f"'{self.habit_name}' ortak serinizi korumak için dondurucu kullanın!", ntype='WARNING')
            
            self.user1_verified_today = False
            self.user2_verified_today = False
            self.last_reset_date = today
            self.save(update_fields=['user1_verified_today', 'user2_verified_today', 'last_reset_date', 'pre_recovery_streak', 'streak', 'recovery_eligible_date'])

    def __str__(self):
        return f"{self.habit_name} Connection: {self.user1.username} <-> {self.user2.username}"


class HabitGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_habit_groups')
    conversation = models.OneToOneField('chat.Conversation', on_delete=models.CASCADE, related_name='habit_group', null=True, blank=True)
    
    streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)
    last_reset_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    # Streak Recovery
    pre_recovery_streak = models.IntegerField(default=0)
    recovery_eligible_date = models.DateField(null=True, blank=True)

    # Adaptation Mode
    adaptation_mode_active = models.BooleanField(default=False)
    adaptation_mode_until = models.DateField(null=True, blank=True)

    def check_and_reset_progress(self):
        import pytz
        from django.utils import timezone
        import datetime
        try:
            user_tz = pytz.timezone(self.creator.timezone)
            today = timezone.now().astimezone(user_tz).date()
        except Exception:
            today = timezone.now().date()

        # 1. Process pending leaves
        cutoff = timezone.now() - datetime.timedelta(hours=24)
        leaving_members = self.memberships.filter(pending_leave_at__lte=cutoff)
        has_leaves = leaving_members.exists()
        for m in leaving_members:
            if self.conversation:
                self.conversation.participants.remove(m.user)
                from chat.models import ChatMessage
                ChatMessage.objects.create(
                    conversation=self.conversation,
                    sender=None,
                    content=f"@{m.user.username} gruptan ayrıldı. Grup 7 günlük Adaptasyon Modu'na girdi!",
                    message_type=ChatMessage.MessageType.TEXT
                )
            self.adaptation_mode_active = True
            self.adaptation_mode_until = today + datetime.timedelta(days=7)
            m.delete()
        if has_leaves:
            self.save(update_fields=['adaptation_mode_active', 'adaptation_mode_until'])

        last_reset = self.last_reset_date
        if isinstance(last_reset, datetime.datetime):
            last_reset = last_reset.date()

        # 2. Reset and verify progress
        if today > last_reset:
            yesterday_date = last_reset
            
            # Check if yesterday was completed
            all_members = self.memberships.all()
            completed_yesterday = all_members.exists() and all(m.verified_today for m in all_members)
            
            if not completed_yesterday:
                if self.adaptation_mode_active:
                    # Sıfır Tolerans!
                    self.streak = 0
                    self.adaptation_mode_active = False
                    self.adaptation_mode_until = None
                    if self.conversation:
                        from chat.models import ChatMessage
                        ChatMessage.objects.create(
                            conversation=self.conversation,
                            sender=None,
                            content="Adaptasyon Modu'nda fire verildi! Grup serisi sıfırlandı.",
                            message_type=ChatMessage.MessageType.TEXT
                        )
                else:
                    # Try proactive save
                    reserve = None
                    if self.conversation:
                        reserve = GroupReserve.objects.filter(conversation=self.conversation, used=False).first()
                        
                    if reserve:
                        reserve.used = True
                        reserve.can_withdraw = False
                        reserve.save(update_fields=['used', 'can_withdraw'])
                        
                        RoomFreezeUsage.objects.create(conversation=self.conversation, date=yesterday_date)
                        
                        if self.conversation:
                            from chat.models import ChatMessage
                            ChatMessage.objects.create(
                                conversation=self.conversation,
                                sender=None,
                                content="Streak automatically saved via Group Reserve",
                                message_type=ChatMessage.MessageType.TEXT
                            )
                    else:
                        # Reactive recovery setup
                        if self.streak > 0:
                            self.pre_recovery_streak = self.streak
                            self.streak = 0
                            self.recovery_eligible_date = yesterday_date
                            
                            if self.conversation:
                                from chat.models import ChatMessage
                                ChatMessage.objects.create(
                                    conversation=self.conversation,
                                    sender=None,
                                    content="Streak in danger! Use a freeze to recover it.",
                                    message_type=ChatMessage.MessageType.TEXT
                                )
                            
                            # Notify users
                            from users.notifications import notify
                            for m in all_members:
                                notify(m.user, "Serin Tehlikede! ❄️", f"'{self.name}' grup serinizi korumak için dondurucu kullanın!", ntype='WARNING')
            
            # 3. Handle adaptation mode completion
            if self.adaptation_mode_active and today > self.adaptation_mode_until:
                self.adaptation_mode_active = False
                self.adaptation_mode_until = None
                if self.conversation:
                    from chat.models import ChatMessage
                    ChatMessage.objects.create(
                        conversation=self.conversation,
                        sender=None,
                        content="Adaptasyon Modu başarıyla tamamlandı! Grup serisi normal takibe döndü.",
                        message_type=ChatMessage.MessageType.TEXT
                    )
            
            self.memberships.all().update(verified_today=False)
            self.last_reset_date = today
            self.save(update_fields=['last_reset_date', 'adaptation_mode_active', 'adaptation_mode_until', 'pre_recovery_streak', 'streak', 'recovery_eligible_date'])

    def __str__(self):
        return f"Group Habit: {self.name}"


class HabitGroupMember(models.Model):
    group = models.ForeignKey(HabitGroup, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='group_memberships')
    verified_today = models.BooleanField(default=False)
    last_verified_date = models.DateField(null=True, blank=True)
    
    # Gentle Departure / 24h Grace Period
    pending_leave_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class GroupReserve(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey('chat.Conversation', on_delete=models.CASCADE, related_name='reserves')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_reserves')
    can_withdraw = models.BooleanField(default=True)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reserve by {self.user.username} in Chat {self.conversation.id}"


class RoomFreezeUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey('chat.Conversation', on_delete=models.CASCADE, related_name='freeze_usages')
    date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('conversation', 'date')

    def __str__(self):
        return f"Freeze applied to Chat {self.conversation.id} on {self.date}"

