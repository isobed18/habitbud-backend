import logging
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Habit
from .forms import HabitForm
from datetime import date, datetime, timedelta
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from .serializers import HabitSerializer
# Create your views here.

# your_app/views.py

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Habit
from .serializers import HabitSerializer
from django.core.cache import cache

class HabitListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import HabitHistory
        from datetime import datetime
        
        date_param = request.query_params.get('date')
        today = date.today()
        target_date = today

        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                pass # Invalid date, fallback to today

        habits = Habit.objects.filter(user=request.user)
        
        # Filter out habits that didn't exist on the target date
        valid_habits = []
        for h in habits:
            # If created_at is None, we assume it's an old habit (always visible)
            if h.created_at and target_date < h.created_at:
                continue
            valid_habits.append(h)
        
        habits = valid_habits
        
        if target_date < today:
            # HISTORICAL VIEW: Fetch snapshot data
            history_map = {
                h.habit_id: h 
                for h in HabitHistory.objects.filter(habit__in=habits, date=target_date)
            }
            
            for habit in habits:
                history = history_map.get(habit.id)
                if history:
                    habit.count = history.count
                    habit.total_time = history.total_time
                else:
                    # No record for past date = 0 progress
                    habit.count = 0
                    if habit.total_time:
                        habit.total_time = timedelta(0)
                        
        else:
            # LIVE VIEW: Apply streak freeze and check/reset progress if needed
            if hasattr(request.user, 'check_and_apply_streak_freeze'):
                try:
                    request.user.check_and_apply_streak_freeze()
                except Exception as e:
                    logging.getLogger(__name__).error(f"Error applying streak freeze: {e}")
            for habit in habits:
                habit.check_and_reset_progress()
            
        serializer = HabitSerializer(habits, many=True)
        return Response(serializer.data)

    def post(self, request):
        from users.entitlements import get_limits
        limits = get_limits(request.user)
        habit_limit = limits.get('habits')
        if habit_limit is not None and Habit.objects.filter(user=request.user).count() >= habit_limit:
            return Response({'error': f'Free plan habit limit reached ({habit_limit}).'}, status=status.HTTP_403_FORBIDDEN)

        serializer = HabitSerializer(data=request.data)
        if serializer.is_valid():
            # The serializer will create the habit and associate the user
            habit = serializer.save(user=request.user)

            # If created from a preset, set up a habit-aware daily reminder.
            template_slug = request.data.get('template_slug')
            if template_slug:
                self._create_reminder_from_template(request.user, habit, template_slug)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _create_reminder_from_template(self, user, habit, template_slug):
        from datetime import time
        from .models import HabitTemplate
        from users.models import Reminder
        try:
            template = HabitTemplate.objects.get(slug=template_slug, is_active=True)
        except HabitTemplate.DoesNotExist:
            return
        Reminder.objects.get_or_create(
            user=user,
            habit=habit,
            defaults={
                'title': f"{template.icon} {habit.name}",
                'message': template.reminder_copy,
                'time': template.reminder_time or time(19, 0),
            },
        )

class HabitDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, habit_id):
        return get_object_or_404(Habit, id=habit_id, user=self.request.user)

    def get(self, request, habit_id):
        habit = self.get_object(habit_id)
        habit.check_and_reset_progress() # Check reset on detail view too
        serializer = HabitSerializer(habit)
        return Response(serializer.data)

    def put(self, request, habit_id):
        habit = self.get_object(habit_id)
        
        serializer = HabitSerializer(habit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        habit.update_and_recalculate()
        habit.lock_schedule_if_needed()
        
        # CACHE TEMİZLEME EKLENDİ
        cache_key = f'user_{request.user.id}_habits'
        cache.delete(cache_key)

        final_serializer = HabitSerializer(habit)
        return Response(final_serializer.data)

    def delete(self, request, habit_id):
        habit = self.get_object(habit_id)
        habit.delete()
        
        # CACHE TEMİZLEME EKLENDİ
        cache_key = f'user_{request.user.id}_habits'
        cache.delete(cache_key)
        
        return Response(status=status.HTTP_204_NO_CONTENT)

class HabitStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, habit_id):
        from users.entitlements import get_limits
        if not get_limits(request.user).get('stats_enabled'):
            return Response({'error': 'Stats are available on the paid plan.'}, status=status.HTTP_403_FORBIDDEN)

        habit = get_object_or_404(Habit, id=habit_id, user=request.user)
        from .models import HabitCompletion, HabitHistory
        
        today = date.today()
        
        # 1. Calendar Data (Merge History + Completion)
        calendar_map = {}
        
        # A. Load History (Snapshots of past days)
        histories = HabitHistory.objects.filter(habit=habit).order_by('date')
        for h in histories:
            status_val = 'missed'
            if h.count > 0:
                status_val = 'partial'
                
            calendar_map[h.date] = {
                "date": h.date.strftime("%Y-%m-%d"),
                "status": status_val,
                "count": h.count
            }
            
        # B. Load Completions (Certified Success)
        completions = HabitCompletion.objects.filter(habit=habit).order_by('completed_at')
        for c in completions:
            date_key = c.completed_at
            # If exists in history (it should), update status. If not, create (rare edge case).
            if date_key in calendar_map:
                calendar_map[date_key]['status'] = 'completed'
            else:
                 calendar_map[date_key] = {
                    "date": date_key.strftime("%Y-%m-%d"),
                    "status": "completed",
                    "count": habit.target_count if habit.target_count else 1
                }

        # C. Add Today's Live Data (Since it's not in history yet)
        if today not in calendar_map:
             current_status = 'missed'
             if habit.count > 0:
                 current_status = 'partial'
             if habit.is_completed_today():
                 current_status = 'completed'
                 
             calendar_map[today] = {
                 "date": today.strftime("%Y-%m-%d"),
                 "status": current_status,
                 "count": habit.count
             }

        # Convert to list and sort
        calendar_data = list(calendar_map.values())
        calendar_data.sort(key=lambda x: x['date'])
        
        # 2. Stats
        total_completions = habit.completed_count
        
        # Calculate completion rate (based on first activity date to today)
        completion_rate = 0.0
        if calendar_data:
            first_date_str = calendar_data[0]['date']
            first_date = datetime.strptime(first_date_str, "%Y-%m-%d").date()
            total_days = (today - first_date).days + 1
            if total_days > 0:
                completion_rate = (total_completions / total_days) * 100
                
        stats = {
            "current_streak": habit.streak,
            "best_streak": habit.best_streak,
            "total_completions": total_completions,
            "completion_rate": round(completion_rate, 1),
            "calendar": calendar_data
        }

        return Response(stats)


from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import HabitTemplate
from .serializers import HabitTemplateSerializer


class HabitTemplateListView(generics.ListAPIView):
    """Predefined habit catalog used by the 'add habit' preset picker."""
    serializer_class = HabitTemplateSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = HabitTemplate.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


