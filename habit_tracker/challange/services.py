from .models import Challenge, UserItem, Achievement
from users.services import UserService
from django.utils import timezone
from django.db import transaction

class ChallengeService:
    @staticmethod
    @transaction.atomic
    def sync_habit_completion(user, habit):
        """
        Called when a habit is completed.
        Updates the specific challenge linked to this habit, or matches by name.
        """
        if habit.challenge:
            active_challenges = Challenge.objects.filter(id=habit.challenge.id, status='ACTIVE')
        else:
            # Fallback for non-auto-created habits that match the name
            active_challenges = Challenge.objects.filter(
                status='ACTIVE'
            ).filter(
                (models.Q(creator=user) | models.Q(partner=user))
            ).filter(habit_name__iexact=habit.name)

        from django.db import models # for Q


        for challenge in active_challenges:
            if user == challenge.creator:
                challenge.creator_completed_today = True
            elif user == challenge.partner:
                challenge.partner_completed_today = True
            
            challenge.save()
            
            ChallengeService._check_and_advance(challenge)

    @staticmethod
    @transaction.atomic
    def _check_and_advance(challenge):
        """Checks if daily conditions are met to increase streak."""
        today = timezone.now().date()
        
        # Don't advance more than once per day
        if challenge.last_update_date == today:
            return

        advanced = False
        if challenge.template.challenge_type == 'SOLO':
            if challenge.creator_completed_today:
                challenge.current_streak += 1
                advanced = True
        else: # DUO
            # All 4 conditions must be met for DUO
            if (challenge.creator_completed_today and 
                challenge.partner_completed_today and 
                challenge.creator_verified_partner and 
                challenge.partner_verified_creator):
                
                challenge.current_streak += 1
                advanced = True
        
        if advanced:
            challenge.last_update_date = today
            # Reset daily flags for tomorrow
            challenge.creator_completed_today = False
            challenge.partner_completed_today = False
            challenge.creator_verified_partner = False
            challenge.partner_verified_creator = False
            
            # Check for completion
            if challenge.current_streak >= challenge.template.duration_days:
                challenge.status = 'COMPLETED'
                ChallengeService._award_rewards(challenge)
            
            challenge.save()

    @staticmethod
    def _award_rewards(challenge):
        """Distributes XP, Points, and Items."""
        template = challenge.template
        participants = [challenge.creator]
        if challenge.partner:
            participants.append(challenge.partner)
        
        for user in participants:
            # 1. Award XP
            UserService.add_xp(user, template.reward_xp)
            
            # 2. Award Points (Explicitly from template, separate from XP-based auto-points if any)
            user.points += template.reward_points
            user.save(update_fields=['points'])
            
            # 3. Award Item
            if template.reward_item:
                UserItem.objects.get_or_create(user=user, item=template.reward_item)
            
            # 3. Create Achievement
            Achievement.objects.create(
                user=user,
                name=f"Champion: {template.name}",
                description=f"Completed the '{template.name}' challenge!",
                challenge=challenge
            )
