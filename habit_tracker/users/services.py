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
        user.points += amount
        
        from .gamification import GamificationEngine
        new_level = GamificationEngine.calculate_level(user.xp)
        
        if new_level > user.level:
            old_level = user.level
            user.level = new_level
            
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
                                'current_xp': user.xp
                            }
                        }
                    )
            except Exception as e:
                print(f"Error sending level up notification: {e}")
            
        user.save(update_fields=['xp', 'level', 'points'])
        return user.level
