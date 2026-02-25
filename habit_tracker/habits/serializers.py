# habits/serializers.py
from rest_framework import serializers
from .models import Habit

class HabitSerializer(serializers.ModelSerializer):
    streak_tier = serializers.SerializerMethodField()
    streak_tier_name = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id', 'name', 'habit_type', 'count', 'target_count', 'streak',
            'completed_count', 'last_completed_date', 'frequency',
            'total_time', 'target_time', 
            'verified_count', 'verification_streak',
            'streak_tier', 'streak_tier_name',
            'color'
        ]
        read_only_fields = [
            'streak', 'completed_count', 'last_completed_date', 
            'verified_count', 'verification_streak',
            'streak_tier', 'streak_tier_name',
        ]

    def get_streak_tier(self, obj):
        tier, _ = obj.streak_tier
        return tier

    def get_streak_tier_name(self, obj):
        _, name = obj.streak_tier
        return name

    def validate(self, data):
        instance = getattr(self, 'instance', None)
        
        habit_type = data.get("habit_type", instance.habit_type if instance else None)
        target_count = data.get("target_count", instance.target_count if instance else None)
        target_time = data.get("target_time", instance.target_time if instance else None)

        if habit_type == 'count' and target_count is None:
            raise serializers.ValidationError({
                "target_count": "Target count is required for count-based habits."
            })
        elif habit_type == 'time' and target_time is None:
             raise serializers.ValidationError({
                "target_time": "Target time is required for time-based habits."
            })
        return data