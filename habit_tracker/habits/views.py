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


from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Count
from friends.models import Friendship
from chat.models import Conversation
from .models import HabitConnection, HabitGroup, HabitGroupMember, GroupReserve, RoomFreezeUsage
from django.utils import timezone
from .serializers import HabitConnectionSerializer, HabitGroupSerializer

User = get_user_model()

class HabitConnectionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        habit_id = request.data.get('habit_id')
        friend_id = request.data.get('friend_id')

        if not habit_id or not friend_id:
            return Response({'error': 'habit_id and friend_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        habit = get_object_or_404(Habit, id=habit_id, user=request.user)
        friend = get_object_or_404(User, id=friend_id)

        # 1. Friendship check
        is_friend = Friendship.objects.filter(
            (Q(from_user=request.user, to_user=friend) | Q(from_user=friend, to_user=request.user)),
            status=Friendship.Status.ACCEPTED
        ).exists()
        if not is_friend:
            return Response({'error': 'Davet göndermek istediğiniz kişiyle arkadaş değilsiniz.'}, status=status.HTTP_403_FORBIDDEN)

        # 2. Duplicate connection check
        existing = HabitConnection.objects.filter(
            (Q(user1=request.user, user2=friend) | Q(user1=friend, user2=request.user)),
            habit_name__iexact=habit.name
        ).exclude(status='declined').first()

        if existing:
            return Response({'error': 'Bu arkadaşınızla bu alışkanlık için zaten bekleyen veya aktif bir bağlantınız var.'}, status=status.HTTP_409_CONFLICT)

        # Check if they share a group for this habit name
        group_exists = HabitGroup.objects.filter(
            memberships__user=request.user,
            name__iexact=habit.name
        ).filter(
            memberships__user=friend
        ).exists()

        if group_exists:
            return Response({'error': f"Bu arkadaşınızla zaten ortak bir '{habit.name}' grubundasınız. Mükerrer bağlara izin verilmez."}, status=status.HTTP_409_CONFLICT)

        # 3. Resolve Friend's Habit
        friend_habit = Habit.objects.filter(user=friend, name__iexact=habit.name).first()

        connection = HabitConnection.objects.create(
            user1=request.user,
            user2=friend,
            habit1=habit,
            habit2=friend_habit,
            habit_name=habit.name,
            status='pending'
        )

        # Send push/in-app notification to the friend
        from users.notifications import notify
        notify(
            friend,
            "Alışkanlık Bağlantı Daveti! 🌱",
            f"{request.user.username} seninle '{habit.name}' alışkanlığını ortak takip etmek istiyor.",
            ntype='INFO'
        )

        return Response(HabitConnectionSerializer(connection, context={'request': request}).data, status=status.HTTP_201_CREATED)


class HabitConnectionRespondView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, connection_id):
        action = request.data.get('action')
        if action not in ['accept', 'decline']:
            return Response({'error': 'Invalid action. Choose accept or decline.'}, status=status.HTTP_400_BAD_REQUEST)

        connection = get_object_or_404(HabitConnection, id=connection_id, user2=request.user, status='pending')

        if action == 'accept':
            # Create/resolve habit for user2
            if not connection.habit2:
                # Check if user already has a habit with the same name (case-insensitive)
                existing_habit = Habit.objects.filter(user=request.user, name__iexact=connection.habit_name).first()
                if existing_habit:
                    connection.habit2 = existing_habit
                else:
                    h1 = connection.habit1
                    connection.habit2 = Habit.objects.create(
                        user=request.user,
                        name=connection.habit_name,
                        habit_type=h1.habit_type,
                        target_count=h1.target_count,
                        target_time=h1.target_time,
                        frequency=h1.frequency,
                        color=h1.color,
                        icon=h1.icon,
                        schedule_type=h1.schedule_type,
                        schedule_weekdays=h1.schedule_weekdays,
                        schedule_target_count=h1.schedule_target_count
                    )
            
            connection.status = 'accepted'
            connection.save()

            # Ensure a 1:1 conversation exists
            conversation = Conversation.objects.annotate(p_count=Count('participants')).filter(
                participants=request.user
            ).filter(
                participants=connection.user1
            ).filter(
                p_count=2
            ).first()

            if not conversation:
                conversation = Conversation.objects.create()
                conversation.participants.add(request.user, connection.user1)

            # Notify user1
            from users.notifications import notify
            notify(
                connection.user1,
                "Bağlantı Daveti Kabul Edildi! 🎉",
                f"{request.user.username} ile '{connection.habit_name}' ortak takibi başladı. Seriyi başlatmak için check atın!",
                ntype='SUCCESS'
            )

        else:
            connection.status = 'declined'
            connection.save()

        return Response(HabitConnectionSerializer(connection, context={'request': request}).data, status=status.HTTP_200_OK)


class HabitConnectionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        connections = HabitConnection.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ).exclude(status='declined')

        for conn in connections:
            conn.check_and_reset_progress()

        return Response(HabitConnectionSerializer(connections, many=True, context={'request': request}).data)


class HabitGroupCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        name = request.data.get('name')
        habit_id = request.data.get('habit_id')
        participant_ids = request.data.get('participant_ids', [])

        if not name or not habit_id or not participant_ids:
            return Response({'error': 'name, habit_id, and participant_ids are required.'}, status=status.HTTP_400_BAD_REQUEST)

        habit = get_object_or_404(Habit, id=habit_id, user=request.user)
        participants = User.objects.filter(id__in=participant_ids)

        all_users = list(participants) + [request.user]

        # 1. Enforce unique connection rules to prevent farming
        # Verify that no two users in the group already share a connection/group for this habit name
        for i in range(len(all_users)):
            for j in range(i + 1, len(all_users)):
                u1 = all_users[i]
                u2 = all_users[j]
                
                # Check direct HabitConnection
                conn_exists = HabitConnection.objects.filter(
                    (Q(user1=u1, user2=u2) | Q(user1=u2, user2=u1)),
                    habit_name__iexact=habit.name
                ).exclude(status='declined').exists()
                
                if conn_exists:
                    return Response({'error': f"Grup üyelerinden '{u1.username}' ve '{u2.username}' zaten '{habit.name}' alışkanlığı için bağlılar. Mükerrer bağlara izin verilmez."}, status=status.HTTP_409_CONFLICT)

                # Check shared HabitGroup
                group_exists = HabitGroup.objects.filter(
                    memberships__user=u1,
                    name__iexact=habit.name
                ).filter(
                    memberships__user=u2
                ).exists()

                if group_exists:
                    return Response({'error': f"Grup üyelerinden '{u1.username}' ve '{u2.username}' zaten ortak bir '{habit.name}' grubundalar."}, status=status.HTTP_409_CONFLICT)

        # 2. Create Chat Conversation Room
        conversation = Conversation.objects.create(
            name=name,
            is_group=True,
            created_by=request.user
        )
        conversation.participants.add(*all_users)

        # 3. Create HabitGroup
        group = HabitGroup.objects.create(
            name=habit.name,
            creator=request.user,
            conversation=conversation
        )

        # 4. Add Creator Membership
        HabitGroupMember.objects.create(
            group=group,
            user=request.user,
            habit=habit
        )

        # 5. Add Participant Memberships
        for p in participants:
            # Find matching habit or auto-create one
            p_habit = Habit.objects.filter(user=p, name__iexact=habit.name).first()
            if not p_habit:
                p_habit = Habit.objects.create(
                    user=p,
                    name=habit.name,
                    habit_type=habit.habit_type,
                    target_count=habit.target_count,
                    target_time=habit.target_time,
                    frequency=habit.frequency,
                    color=habit.color,
                    icon=habit.icon,
                    schedule_type=habit.schedule_type,
                    schedule_weekdays=habit.schedule_weekdays,
                    schedule_target_count=habit.schedule_target_count
                )
            
            HabitGroupMember.objects.create(
                group=group,
                user=p,
                habit=p_habit
            )

            # Notify participant
            from users.notifications import notify
            notify(
                p,
                f"Yeni Alışkanlık Grubu: {name}! 👥",
                f"{request.user.username} seni '{habit.name}' ortak alışkanlık grubuna ekledi.",
                ntype='INFO'
            )

        return Response(HabitGroupSerializer(group, context={'request': request}).data, status=status.HTTP_201_CREATED)


class HabitGroupListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = HabitGroup.objects.filter(memberships__user=request.user).distinct()

        for group in groups:
            group.check_and_reset_progress()

        return Response(HabitGroupSerializer(groups, many=True, context={'request': request}).data)


class HabitGroupLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, group_id):
        group = get_object_or_404(HabitGroup, id=group_id)
        member = get_object_or_404(HabitGroupMember, group=group, user=request.user)

        member.pending_leave_at = timezone.now()
        member.save(update_fields=['pending_leave_at'])

        if group.conversation:
            from chat.models import ChatMessage
            ChatMessage.objects.create(
                conversation=group.conversation,
                sender=None,
                content=f"@{request.user.username} gruptan ayrılma talebinde bulundu. 24 saat sonra gruptan çıkarılacak.",
                message_type=ChatMessage.MessageType.TEXT
            )

        return Response({'message': 'Ayrılma talebi alındı. 24 saat sonra gruptan ayrılacaksınız.'})


class StreakRecoveryView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if request.user not in conversation.participants.all():
            return Response({'error': 'Bu konuşmanın katılımcısı değilsiniz.'}, status=status.HTTP_403_FORBIDDEN)

        # Resolve model
        group = getattr(conversation, 'habit_group', None)
        model = None
        if group:
            model = group
        else:
            model = HabitConnection.objects.filter(
                (Q(user1=request.user) & Q(user2__in=conversation.participants.all())) |
                (Q(user2=request.user) & Q(user1__in=conversation.participants.all())),
                status='accepted'
            ).first()

        if not model:
            return Response({'error': 'Bu konuşma için bir bağlantı veya grup bulunamadı.'}, status=status.HTTP_400_BAD_REQUEST)

        if group and group.adaptation_mode_active:
            return Response({'error': 'Grup Adaptasyon Modunda, dondurucu kullanılamaz!'}, status=status.HTTP_400_BAD_REQUEST)

        if not model.recovery_eligible_date:
            return Response({'error': 'Bu oda için dondurucu ile kurtarılabilecek aktif bir kırılma yok.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.streak_freezes <= 0:
            return Response({'error': 'Yeterli dondurucunuz yok.'}, status=status.HTTP_400_BAD_REQUEST)

        # Spend freeze
        request.user.streak_freezes -= 1
        request.user.save(update_fields=['streak_freezes'])

        # Create usage record
        RoomFreezeUsage.objects.create(conversation=conversation, date=model.recovery_eligible_date)

        # Restore streak
        model.streak = model.pre_recovery_streak
        model.recovery_eligible_date = None
        model.save(update_fields=['streak', 'recovery_eligible_date'])

        # Chat notification
        from chat.models import ChatMessage
        ChatMessage.objects.create(
            conversation=conversation,
            sender=None,
            content=f"Streak saved by @{request.user.username}",
            message_type=ChatMessage.MessageType.TEXT
        )

        return Response({
            'message': 'Seri başarıyla kurtarıldı!',
            'streak': model.streak,
            'streak_freezes': request.user.streak_freezes
        })


class GroupReserveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if request.user not in conversation.participants.all():
            return Response({'error': 'Katılımcı değilsiniz.'}, status=status.HTTP_403_FORBIDDEN)

        reserves = GroupReserve.objects.filter(conversation=conversation, used=False)
        data = [{
            'id': r.id,
            'username': r.user.username,
            'user_id': r.user.id,
            'can_withdraw': r.can_withdraw and (r.user == request.user),
            'created_at': r.created_at
        } for r in reserves]
        return Response(data)

    @transaction.atomic
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if request.user not in conversation.participants.all():
            return Response({'error': 'Katılımcı değilsiniz.'}, status=status.HTTP_403_FORBIDDEN)

        group = getattr(conversation, 'habit_group', None)
        if group and group.adaptation_mode_active:
            return Response({'error': 'Grup Adaptasyon Modunda, dondurucu rezerve edilemez!'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.streak_freezes <= 0:
            return Response({'error': 'Yeterli dondurucunuz yok.'}, status=status.HTTP_400_BAD_REQUEST)

        # Reserve freeze
        request.user.streak_freezes -= 1
        request.user.save(update_fields=['streak_freezes'])

        GroupReserve.objects.create(conversation=conversation, user=request.user)

        # Chat notification
        from chat.models import ChatMessage
        ChatMessage.objects.create(
            conversation=conversation,
            sender=None,
            content=f"@{request.user.username} rezerve dondurucu ekledi.",
            message_type=ChatMessage.MessageType.TEXT
        )

        return Response({
            'message': 'Dondurucu başarıyla rezerve edildi.',
            'streak_freezes': request.user.streak_freezes
        })

    @transaction.atomic
    def delete(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if request.user not in conversation.participants.all():
            return Response({'error': 'Katılımcı değilsiniz.'}, status=status.HTTP_403_FORBIDDEN)

        reserve = GroupReserve.objects.filter(
            conversation=conversation,
            user=request.user,
            used=False,
            can_withdraw=True
        ).first()

        if not reserve:
            return Response({'error': 'Geri çekilebilecek aktif rezerv dondurucu bulunamadı.'}, status=status.HTTP_400_BAD_REQUEST)

        # Return freeze
        request.user.streak_freezes += 1
        request.user.save(update_fields=['streak_freezes'])

        reserve.delete()

        # Chat notification
        from chat.models import ChatMessage
        ChatMessage.objects.create(
            conversation=conversation,
            sender=None,
            content=f"@{request.user.username} rezerve dondurucusunu geri çekti.",
            message_type=ChatMessage.MessageType.TEXT
        )

        return Response({
            'message': 'Rezerve dondurucu geri çekildi.',
            'streak_freezes': request.user.streak_freezes
        })
