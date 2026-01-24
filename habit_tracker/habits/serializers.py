# habits/serializers.py
from rest_framework import serializers
from .models import Habit

class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = [
            'id', 'name', 'habit_type', 'count', 'target_count', 'streak',
            'completed_count', 'last_completed_date', 'frequency',
            'total_time', 'target_time', 
            'verified_count', 'verification_streak',
            'ai_streak', 'last_ai_verification_date',
            'color'
        ]
        read_only_fields = ['streak', 'completed_count', 'last_completed_date', 'verified_count', 'verification_streak', 'ai_streak', 'last_ai_verification_date']

    def validate(self, data):
        # Instance varsa (Update işlemi), mevcut değerleri al, yoksa data'dan al
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