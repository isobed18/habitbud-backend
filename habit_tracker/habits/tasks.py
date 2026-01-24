from celery import shared_task
from .models import Habit
from django.utils import timezone

@shared_task
def reset_habits():
    """Reset habits based on their frequency"""
    today = timezone.now().date()
    habits = Habit.objects.all()
    
    for habit in habits:
        if habit.should_reset_count():
            habit.reset_count() 