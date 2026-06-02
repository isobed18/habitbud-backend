# habits/serializers.py
from rest_framework import serializers
from .models import Habit, HabitTemplate

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
            'color', 'icon',
            'schedule_type', 'schedule_weekdays', 'schedule_target_count', 'schedule_locked',
        ]
        read_only_fields = [
            'streak', 'completed_count', 'last_completed_date', 
            'verified_count', 'verification_streak',
            'streak_tier', 'streak_tier_name', 'schedule_locked',
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

        schedule_type = data.get("schedule_type", instance.schedule_type if instance else "daily")
        weekdays = data.get("schedule_weekdays", instance.schedule_weekdays if instance else "")
        schedule_target = data.get("schedule_target_count", instance.schedule_target_count if instance else 1) or 1
        try:
            schedule_target = int(schedule_target)
        except (TypeError, ValueError):
            raise serializers.ValidationError({"schedule_target_count": "Schedule target must be a number."})

        if schedule_type == 'specific_weekdays':
            try:
                selected = {int(x) for x in str(weekdays).split(',') if x != ''}
            except ValueError:
                raise serializers.ValidationError({"schedule_weekdays": "Weekdays must be comma-separated numbers."})
            if not selected or any(day < 0 or day > 6 for day in selected):
                raise serializers.ValidationError({"schedule_weekdays": "Select at least one weekday between 0 and 6."})

        if schedule_type == 'weekly_count' and not (1 <= schedule_target <= 7):
            raise serializers.ValidationError({"schedule_target_count": "Weekly target must be between 1 and 7."})
        if schedule_type == 'monthly_count' and not (1 <= schedule_target <= 31):
            raise serializers.ValidationError({"schedule_target_count": "Monthly target must be between 1 and 31."})

        if instance and instance.schedule_locked:
            locked_fields = {'frequency', 'schedule_type', 'schedule_weekdays', 'schedule_target_count'}
            if any(field in data and data[field] != getattr(instance, field) for field in locked_fields):
                raise serializers.ValidationError({
                    "schedule": "Schedule cannot be changed after this habit has progress."
                })
        return data


class HabitTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitTemplate
        fields = [
            'id', 'slug', 'name', 'icon', 'category', 'color',
            'habit_type', 'default_target_count', 'default_frequency',
            'reminder_copy', 'reminder_time',
        ]
