import logging
from django.db import transaction
from .models import CustomUser

class UserService:
    @staticmethod
    @transaction.atomic
    def add_xp(user: CustomUser, amount: int):
        """
        Adds XP to the user and recalculates level.
        Uses GamificationEngine for advanced curve logic.
        """
        user.xp += amount
        
        from .gamification import GamificationEngine
        new_level = GamificationEngine.calculate_level(user.xp)
        
        diamond_bonus = 0
        if new_level > user.level:
            old_level = user.level
            user.level = new_level
            diamond_bonus = new_level * 5
            user.points += diamond_bonus
            
            # Trigger level up notification via WebSocket
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"user_{user.id}",
                        {
                            'type': 'system_notification',
                            'notification_type': 'level_up',
                            'data': {
                                'old_level': old_level,
                                'new_level': new_level,
                                'current_xp': user.xp,
                                'diamond_bonus': diamond_bonus,
                                'points': user.points
                            }
                        }
                    )
            except Exception as e:
                logging.getLogger(__name__).error(f"Error sending level up notification: {e}")
            
        user.save(update_fields=['xp', 'level', 'points'])
        return user.level

    @staticmethod
    @transaction.atomic
    def add_points(user: CustomUser, amount: int):
        """
        Adds points (diamonds) to the user explicitly.
        """
        user.points += amount
        user.save(update_fields=['points'])
        return user.points
