# chat/views.py
import logging
import json
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from .models import Conversation, ChatMessage, LiveRoomJoinRequest
from .serializers import ConversationSerializer, ChatMessageSerializer
from friends.models import Friendship
from django.db.models import Q, Count
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()

class StartConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        target_user_id = request.data.get('user_id')
        if not target_user_id:
            return Response({'error': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        target_user = get_object_or_404(User, id=target_user_id)
        user = request.user

        if user == target_user:
            return Response({'error': 'You cannot start a conversation with yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        # Block check (either direction).
        from users.models import Block
        if Block.objects.filter(
            (Q(blocker=user, blocked=target_user) | Q(blocker=target_user, blocked=user))
        ).exists():
            return Response({'error': 'Bu kullanıcıya mesaj gönderemezsin.'}, status=status.HTTP_403_FORBIDDEN)

        is_friend = Friendship.objects.filter(
            (Q(from_user=user, to_user=target_user) | Q(from_user=target_user, to_user=user)),
            status=Friendship.Status.ACCEPTED
        ).exists()

        # Respect the target's message-privacy setting.
        privacy = getattr(target_user, 'message_privacy', 'everyone')
        if privacy == 'nobody':
            return Response({'error': 'Bu kullanıcı mesaj almıyor.'}, status=status.HTTP_403_FORBIDDEN)
        if privacy == 'friends' and not is_friend:
            return Response({'error': 'Bu kullanıcıya yalnızca arkadaşları mesaj atabilir.'}, status=status.HTTP_403_FORBIDDEN)

        conversation = Conversation.objects.annotate(participant_count=Count('participants')).filter(
            participants=user
        ).filter(
            participants=target_user
        ).filter(
            participant_count=2
        ).first()

        if conversation:
            serializer = ConversationSerializer(conversation, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            new_conversation = Conversation.objects.create()
            new_conversation.participants.add(user, target_user)
            serializer = ConversationSerializer(new_conversation, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.conversations.all().distinct()


class ConversationDetailView(generics.RetrieveAPIView):
    """Conversation info (participants, group name, is_group) for the chat header."""
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'conversation_id'

    def get_queryset(self):
        return self.request.user.conversations.all().distinct()


class CreateRoomView(APIView):
    """Create a group chat room with the given friends.

    POST { "name": "Gym Buddies", "participant_ids": ["uuid", ...] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        name = (request.data.get('name') or '').strip()
        participant_ids = request.data.get('participant_ids', []) or []
        if not name:
            return Response({'error': 'name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        live_room_type = request.data.get('live_room_type') or Conversation.LiveRoomType.GENERAL
        if live_room_type not in Conversation.LiveRoomType.values:
            return Response({'error': 'Invalid live_room_type.'}, status=status.HTTP_400_BAD_REQUEST)

        privacy = request.data.get('privacy') or Conversation.RoomPrivacy.FRIENDS
        if privacy not in Conversation.RoomPrivacy.values:
            return Response({'error': 'Invalid privacy.'}, status=status.HTTP_400_BAD_REQUEST)

        join_policy = request.data.get('join_policy') or Conversation.JoinPolicy.OPEN
        if join_policy not in Conversation.JoinPolicy.values:
            return Response({'error': 'Invalid join_policy.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            capacity = max(2, min(int(request.data.get('capacity') or 8), 50))
            work_minutes = max(1, min(int(request.data.get('pomodoro_work_minutes') or 25), 180))
            break_minutes = max(1, min(int(request.data.get('pomodoro_break_minutes') or 5), 60))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid room timer settings.'}, status=status.HTTP_400_BAD_REQUEST)

        required_habit_slug = request.data.get('required_habit_slug') or ''
        if live_room_type == Conversation.LiveRoomType.STUDY:
            required_habit_slug = required_habit_slug or 'study'
        elif live_room_type == Conversation.LiveRoomType.WORKOUT:
            required_habit_slug = required_habit_slug or 'workout'

        room = Conversation.objects.create(
            name=name,
            is_group=True,
            created_by=request.user,
            live_room_type=live_room_type,
            required_habit_slug=required_habit_slug,
            capacity=capacity,
            privacy=privacy,
            join_policy=join_policy,
            pomodoro_work_minutes=work_minutes,
            pomodoro_break_minutes=break_minutes,
        )
        room.participants.add(request.user)

        for uid in participant_ids:
            try:
                friend = User.objects.get(id=uid)
            except (User.DoesNotExist, ValueError, TypeError):
                continue
            is_friend = Friendship.objects.filter(
                (Q(from_user=request.user, to_user=friend) | Q(from_user=friend, to_user=request.user)),
                status=Friendship.Status.ACCEPTED
            ).exists()
            if is_friend:
                if room.participants.count() >= room.capacity:
                    break
                room.participants.add(friend)

        serializer = ConversationSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoomMembershipView(APIView):
    """Join (POST) or leave (DELETE) a group chat room."""
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id, *args, **kwargs):
        room = get_object_or_404(Conversation, id=conversation_id, is_group=True)
        if room.participants.count() >= room.capacity:
            return Response({'error': 'Room is full.'}, status=status.HTTP_400_BAD_REQUEST)
        if room.join_policy == Conversation.JoinPolicy.REQUEST and room.created_by != request.user:
            return Response({'error': 'Join request flow is not enabled yet for this room.'}, status=status.HTTP_403_FORBIDDEN)
        room.participants.add(request.user)
        return Response(ConversationSerializer(room, context={'request': request}).data)

    def delete(self, request, conversation_id, *args, **kwargs):
        room = get_object_or_404(Conversation, id=conversation_id, is_group=True)
        room.participants.remove(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LiveRoomDiscoveryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Conversation.objects.filter(
            is_group=True,
            privacy=Conversation.RoomPrivacy.PUBLIC,
        ).exclude(live_room_type=Conversation.LiveRoomType.GENERAL).prefetch_related('participants')

        room_type = request.query_params.get('type')
        if room_type in Conversation.LiveRoomType.values:
            qs = qs.filter(live_room_type=room_type)

        rooms = []
        for room in qs.order_by('-created_at')[:50]:
            data = ConversationSerializer(room, context={'request': request}).data
            data['participant_count'] = room.participants.count()
            data['has_join_request'] = LiveRoomJoinRequest.objects.filter(room=room, user=request.user, status='pending').exists()
            rooms.append(data)
        return Response(rooms)


class LiveRoomJoinRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        room = get_object_or_404(Conversation, id=conversation_id, is_group=True, created_by=request.user)
        data = [
            {
                'id': str(req.id),
                'user': {'id': str(req.user.id), 'username': req.user.username},
                'status': req.status,
                'created_at': req.created_at,
            }
            for req in room.join_requests.filter(status='pending').select_related('user')
        ]
        return Response(data)

    def post(self, request, conversation_id):
        room = get_object_or_404(Conversation, id=conversation_id, is_group=True)
        if request.user in room.participants.all():
            return Response({'error': 'Already a member.'}, status=status.HTTP_400_BAD_REQUEST)
        if room.participants.count() >= room.capacity:
            return Response({'error': 'Room is full.'}, status=status.HTTP_400_BAD_REQUEST)
        if room.join_policy == Conversation.JoinPolicy.OPEN:
            room.participants.add(request.user)
            return Response(ConversationSerializer(room, context={'request': request}).data)

        req, _ = LiveRoomJoinRequest.objects.update_or_create(
            room=room,
            user=request.user,
            defaults={'status': 'pending'},
        )
        return Response({'id': str(req.id), 'status': req.status}, status=status.HTTP_201_CREATED)


class LiveRoomJoinRequestRespondView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        action = request.data.get('action')
        if action not in ['accept', 'decline']:
            return Response({'error': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)
        req = get_object_or_404(LiveRoomJoinRequest, id=request_id, room__created_by=request.user, status='pending')
        if action == 'accept':
            if req.room.participants.count() >= req.room.capacity:
                return Response({'error': 'Room is full.'}, status=status.HTTP_400_BAD_REQUEST)
            req.room.participants.add(req.user)
            req.status = 'accepted'
        else:
            req.status = 'declined'
        req.save(update_fields=['status'])
        return Response({'status': req.status})

class MessageListView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if self.request.user not in conversation.participants.all():
            return ChatMessage.objects.none()
        return conversation.messages.all()

class MessageCreateView(generics.CreateAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if self.request.user not in conversation.participants.all():
             raise PermissionDenied("You are not a participant of this conversation.")

        message = serializer.save(sender=self.request.user, conversation=conversation)
        
        if message.message_type == ChatMessage.MessageType.PROOF:
            self.broadcast_proof_message(message)

    def broadcast_proof_message(self, message):
        channel_layer = get_channel_layer()
        if channel_layer:
            room_group_name = f'chat_{message.conversation.id}'
            message_data = ChatMessageSerializer(message).data
            # UUID FIX:
            clean_message_data = json.loads(json.dumps(message_data, default=str))
            
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {'type': 'chat_message', 'message': clean_message_data}
            )

class ProofSubmissionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Social Proof Submission: Sends a proof image to a friend/conversation.
        """
        from users.entitlements import get_limits, today
        limits = get_limits(request.user)
        submit_limit = limits.get('proof_submissions_per_day')
        if submit_limit is not None:
            used = ChatMessage.objects.filter(
                sender=request.user,
                message_type=ChatMessage.MessageType.PROOF,
                created_at__date=today(),
            ).count()
            if used >= submit_limit:
                return Response({'error': f'Free plan daily proof submission limit reached ({submit_limit}).'}, status=status.HTTP_403_FORBIDDEN)

        habit_id = request.data.get('habit_id')
        conversation_id = request.data.get('conversation_id')
        friend_id = request.data.get('friend_id')
        proof_image = request.FILES.get('proof_image')
        content = request.data.get('content', '')

        if not habit_id or not proof_image:
            return Response({'error': 'habit_id and proof_image are required.'}, status=status.HTTP_400_BAD_REQUEST)

        from habits.models import Habit
        habit = get_object_or_404(Habit, id=habit_id, user=request.user)
        
        # Habit must be completed today before sending proof
        is_live_room = False
        if conversation_id:
            try:
                candidate = Conversation.objects.get(id=conversation_id)
                is_live_room = candidate.is_live_room
            except Conversation.DoesNotExist:
                is_live_room = False

        if is_live_room:
            if not habit.has_progress_today():
                return Response({'error': 'Start this habit before submitting a live-room check.'}, status=status.HTTP_400_BAD_REQUEST)
        elif not habit.is_completed_today():
            return Response({'error': 'Habit must be completed before submitting proof.'}, status=status.HTTP_400_BAD_REQUEST)

        
        # 1. Resolve Conversation (Social Only)
        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id)
        else:
            if not friend_id:
                 return Response({'error': 'conversation_id or friend_id is required for Social Proof.'}, status=status.HTTP_400_BAD_REQUEST)

            # Resolve Friend -> Conversation
            friend = get_object_or_404(User, id=friend_id)
            is_friend = Friendship.objects.filter(
                (Q(from_user=request.user, to_user=friend) | Q(from_user=friend, to_user=request.user)),
                status=Friendship.Status.ACCEPTED
            ).exists()
            
            if not is_friend:
                return Response({'error': 'Not friends.'}, status=status.HTTP_403_FORBIDDEN)
            
            conversation = Conversation.objects.annotate(participant_count=Count('participants')).filter(
                participants=request.user).filter(participants=friend).filter(participant_count=2).first()
            
            if not conversation:
                conversation = Conversation.objects.create()
                conversation.participants.add(request.user, friend)

        if request.user not in conversation.participants.all():
            raise PermissionDenied("Not a participant.")

        # 2. Create Message (Pending by default, friend verifies)
        proof_message = ChatMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=ChatMessage.MessageType.PROOF,
            proof_image=proof_image,
            related_habit=habit,
            verification_status=ChatMessage.VerificationStatus.PENDING
        )

        # Flat "paper-plane" reward for sending a check.
        from users.gamification import GamificationEngine
        from users.services import UserService
        UserService.add_xp(request.user, GamificationEngine.BASE_SUBMIT_XP)

        self.broadcast_proof_message(proof_message)
        return Response(
            {
                **ChatMessageSerializer(proof_message).data,
                'xp_earned': GamificationEngine.BASE_SUBMIT_XP,
            },
            status=status.HTTP_201_CREATED,
        )

    def broadcast_proof_message(self, message):
        channel_layer = get_channel_layer()
        if channel_layer:
            room_group_name = f'chat_{message.conversation.id}'
            message_data = ChatMessageSerializer(message).data
            # UUID FIX:
            clean_message_data = json.loads(json.dumps(message_data, default=str))
            
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {'type': 'chat_message', 'message': clean_message_data}
            )

class RecallCheckView(APIView):
    """Undo a just-sent check: the sender deletes their own PENDING check and
    the +5 submit XP is refunded. Used by the post-share 'Geri Al' window."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, message_id, *args, **kwargs):
        msg = get_object_or_404(
            ChatMessage, id=message_id, message_type=ChatMessage.MessageType.PROOF
        )
        if msg.sender != request.user:
            return Response({'error': 'Not your check.'}, status=status.HTTP_403_FORBIDDEN)
        if msg.verification_status == ChatMessage.VerificationStatus.VERIFIED:
            return Response({'error': 'Already approved, cannot recall.'}, status=status.HTTP_400_BAD_REQUEST)

        from users.gamification import GamificationEngine
        from users.services import UserService
        UserService.add_xp(request.user, -GamificationEngine.BASE_SUBMIT_XP)
        msg.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyProofView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, message_id, *args, **kwargs):
        action = request.data.get('action')
        if action not in ['verify', 'reject']:
            return Response({'error': "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        proof_message = get_object_or_404(ChatMessage, id=message_id, message_type=ChatMessage.MessageType.PROOF)
        
        if request.user == proof_message.sender:
            return Response({'error': 'Cannot verify own proof.'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user not in proof_message.conversation.participants.all():
            return Response({'error': 'Not a participant.'}, status=status.HTTP_403_FORBIDDEN)

        # Idempotency / anti-farm: a check can only be acted on once (PENDING).
        if proof_message.verification_status != ChatMessage.VerificationStatus.PENDING:
            return Response({'error': 'Bu check zaten işlendi.'}, status=status.HTTP_409_CONFLICT)

        from users.entitlements import get_limits, today
        limits = get_limits(request.user)
        verify_limit = limits.get('proof_verifications_per_day')
        if action == 'verify' and verify_limit is not None:
            used = ChatMessage.objects.filter(
                conversation__participants=request.user,
                message_type=ChatMessage.MessageType.PROOF,
                verification_status=ChatMessage.VerificationStatus.VERIFIED,
                created_at__date=today(),
            ).exclude(sender=request.user).count()
            if used >= verify_limit:
                return Response({'error': f'Free plan daily verification limit reached ({verify_limit}).'}, status=status.HTTP_403_FORBIDDEN)

        sender_xp = 0
        sender_diamonds = 0
        verifier_xp = 0
        verifier_diamonds = 0

        if action == 'verify':
            habit = proof_message.related_habit
            conversation = proof_message.conversation
            is_live_room = bool(conversation and conversation.is_live_room)
            is_group = bool(conversation and conversation.is_group and not is_live_room)
            
            if habit:
                # STRICT CHECK: Habit must be completed today to accept verification
                if not is_live_room and not habit.is_completed_today():
                    return Response({'error': 'Habit is not completed today. Cannot verify.'}, status=status.HTTP_400_BAD_REQUEST)
                if is_live_room and not habit.has_progress_today():
                    return Response({'error': 'Habit has no progress today. Cannot verify.'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Update Verification Streak & Stats
                if habit.is_completed_today():
                    habit.update_verification_streak()
                
            proof_message.verification_status = ChatMessage.VerificationStatus.VERIFIED
            proof_message.save()
            
            from users.gamification import GamificationEngine
            from users.services import UserService
            from habits.models import HabitConnection, HabitGroup, HabitGroupMember
            from users.notifications import notify
            import datetime
            today_date = datetime.date.today()
            yesterday_date = today_date - datetime.timedelta(days=1)

            # Resolve if it is a Duo Connection or Group Habit
            duo_conn = None
            group_habit = None
            
            if is_group:
                # Group Flow
                group_habit = getattr(conversation, 'habit_group', None)
                if group_habit:
                    group_habit.check_and_reset_progress()
                    member = HabitGroupMember.objects.filter(group=group_habit, user=proof_message.sender).first()
                    if member:
                        member.verified_today = True
                        member.last_verified_date = today_date
                        member.save()

                    # Check if all members are verified today
                    all_members = group_habit.memberships.all()
                    if all(m.verified_today for m in all_members):
                        # Group Completed today!
                        if group_habit.last_completed_date != today_date:
                            if group_habit.adaptation_mode_active:
                                group_habit.last_completed_date = today_date
                                group_habit.save()
                                ChatMessage.objects.create(
                                    conversation=conversation,
                                    sender=None,
                                    content="Bugün herkes hedefini tamamladı! (Grup Adaptasyon Modunda, seri ilerlemedi)",
                                    message_type=ChatMessage.MessageType.TEXT
                                )
                            else:
                                if group_habit.last_completed_date == yesterday_date:
                                    group_habit.streak += 1
                                else:
                                    group_habit.streak = 1
                                group_habit.best_streak = max(group_habit.best_streak, group_habit.streak)
                                group_habit.last_completed_date = today_date
                                group_habit.save()

                                # Group Complete Bonus to all members
                                for m in all_members:
                                    UserService.add_xp(m.user, 50)
                                    UserService.add_points(m.user, 10)
                                    notify(
                                        m.user,
                                        f"Grup Alışkanlığı Tamamlandı! 🔥 (Seri: {group_habit.streak})",
                                        f"'{group_habit.name}' grubundaki herkes hedefini tamamladı! +50 XP ve +10 💎 kazandınız!",
                                        ntype='SUCCESS'
                                    )
                                # WebSocket broadcast for group completion
                                try:
                                    channel_layer = get_channel_layer()
                                    if channel_layer:
                                        async_to_sync(channel_layer.group_send)(
                                            f"user_{m.user.id}",
                                            {
                                                'type': 'system_notification',
                                                'notification_type': 'group_completed',
                                                'data': {'group_id': str(group_habit.id), 'streak': group_habit.streak}
                                            }
                                        )
                                except Exception:
                                    pass
            else:
                # Duo Flow
                friend = conversation.participants.exclude(id=proof_message.sender.id).first()
                if friend:
                    duo_conn = HabitConnection.objects.filter(
                        (Q(user1=proof_message.sender, user2=friend) & Q(habit1=habit)) |
                        (Q(user1=friend, user2=proof_message.sender) & Q(habit2=habit)),
                        status='accepted'
                    ).first()
                    if duo_conn:
                        duo_conn.check_and_reset_progress()
                        if duo_conn.user1 == proof_message.sender:
                            duo_conn.user1_verified_today = True
                        else:
                            duo_conn.user2_verified_today = True
                        duo_conn.save()

                        # Check if both are verified
                        if duo_conn.user1_verified_today and duo_conn.user2_verified_today:
                            if duo_conn.last_completed_date != today_date:
                                if duo_conn.last_completed_date == yesterday_date:
                                    duo_conn.streak += 1
                                else:
                                    duo_conn.streak = 1
                                duo_conn.best_streak = max(duo_conn.best_streak, duo_conn.streak)
                                duo_conn.last_completed_date = today_date
                                duo_conn.save()

                                # Duo Complete Bonus to both
                                for u in [duo_conn.user1, duo_conn.user2]:
                                    UserService.add_xp(u, 15)
                                    UserService.add_points(u, 3)
                                    notify(
                                        u,
                                        f"Ortak Seri Tamamlandı! 🥂 (Seri: {duo_conn.streak})",
                                        f"'{duo_conn.habit_name}' alışkanlığını bugün ikiniz de tamamladınız! +15 XP ve +3 💎 kazandınız!",
                                        ntype='SUCCESS'
                                    )
            
            # Get friendship for streak multiplier
            friend_streak = 0
            try:
                friendship = Friendship.objects.filter(
                    (Q(from_user=request.user, to_user=proof_message.sender) | 
                     Q(from_user=proof_message.sender, to_user=request.user)),
                    status=Friendship.Status.ACCEPTED
                ).first()
                if friendship:
                    friendship.update_streak()
                    friend_streak = friendship.streak
            except Exception as e:
                logging.getLogger(__name__).error(f"Error updating friendship streak: {e}")

            # Calculate base rewards depending on Duo or Group
            if group_habit:
                # Group reward (Higher)
                base_verify_xp = 30
                base_verifier_xp = 20
                sender_diamonds = 3
                verifier_diamonds = 2
            elif duo_conn:
                # Duo reward (Medium)
                base_verify_xp = 15
                base_verifier_xp = 10
                sender_diamonds = 2
                verifier_diamonds = 1
            else:
                # Solo fallback reward (Legacy)
                base_verify_xp = 4 if is_live_room else GamificationEngine.BASE_VERIFY_XP
                base_verifier_xp = 1 if is_live_room else GamificationEngine.BASE_VERIFIER_XP
                sender_diamonds = 1
                verifier_diamonds = 1

            # Adjust habit streak depending on context
            if group_habit:
                habit_streak = group_habit.streak
                h_mult = GamificationEngine.calculate_habit_streak_multiplier(habit_streak) + 0.5
                f_mult = GamificationEngine.calculate_friend_streak_multiplier(friend_streak)
                sender_xp = int(round(base_verify_xp * h_mult * f_mult))
            elif duo_conn:
                habit_streak = duo_conn.streak
                sender_xp, h_mult, f_mult = GamificationEngine.calculate_full_reward(
                    base_verify_xp, habit_streak, friend_streak
                )
            else:
                habit_streak = habit.verification_streak if habit else 0
                sender_xp, h_mult, f_mult = GamificationEngine.calculate_full_reward(
                    base_verify_xp, habit_streak, friend_streak
                )

            # Add sender rewards
            UserService.add_xp(proof_message.sender, sender_xp)
            UserService.add_points(proof_message.sender, sender_diamonds)
            
            # Add verifier rewards
            verifier_xp = int(round(base_verifier_xp *
                            GamificationEngine.calculate_friend_streak_multiplier(friend_streak)))
            UserService.add_xp(request.user, verifier_xp)
            UserService.add_points(request.user, verifier_diamonds)

            # Notify sender
            from users.notifications import notify
            habit_name = habit.name if habit else 'alışkanlık'
            notify(
                proof_message.sender,
                "Check'in onaylandı! 🔥",
                f"{request.user.username}, {habit_name} check'ini onayladı. +{sender_xp} XP ve +{sender_diamonds} 💎 kazandın!",
                ntype='CHECK',
                data={'habit_id': str(habit.id) if habit else None, 'xp': sender_xp, 'points': sender_diamonds},
            )

            # Broadcast verify state update to conversation room via WebSockets
            channel_layer = get_channel_layer()
            if channel_layer:
                room_group_name = f'chat_{proof_message.conversation.id}'
                message_data = ChatMessageSerializer(proof_message).data
                clean_message_data = json.loads(json.dumps(message_data, default=str))
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {'type': 'chat_message', 'message': clean_message_data}
                )

        elif action == 'reject':
            proof_message.verification_status = ChatMessage.VerificationStatus.REJECTED
            proof_message.save()

            # Notify sender
            from users.notifications import notify
            notify(
                proof_message.sender,
                "Kanıt Reddedildi ❌",
                f"{request.user.username} '{proof_message.related_habit.name}' kanıtını reddetti. Yeni bir kanıt yüklemeyi dene.",
                ntype='ERROR'
            )

            # Broadcast reject state update to conversation room via WebSockets
            channel_layer = get_channel_layer()
            if channel_layer:
                room_group_name = f'chat_{proof_message.conversation.id}'
                message_data = ChatMessageSerializer(proof_message).data
                clean_message_data = json.loads(json.dumps(message_data, default=str))
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {'type': 'chat_message', 'message': clean_message_data}
                )

        return Response({
            'status': proof_message.verification_status,
            'sender_xp_earned': sender_xp,
            'sender_diamonds_earned': sender_diamonds,
            'verifier_xp_earned': verifier_xp,
            'verifier_diamonds_earned': verifier_diamonds,
        }, status=status.HTTP_200_OK)

from .models import Story
from .serializers import StorySerializer

class StoryCreateView(generics.CreateAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class StoryFeedView(APIView):
    """
    Returns active stories grouped by user.
    Response:
    [
      { 
        "user_id": "uuid", "username": "...", "avatar": "...", 
        "stories": [ { ...story_data... }, ... ] 
      },
      ...
    ]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        from collections import defaultdict
        user = self.request.user
        
        # 1. Provide a list of "users to watch" (Friends + Self)
        friends = Friendship.objects.filter(
            (Q(from_user=user) | Q(to_user=user)),
            status=Friendship.Status.ACCEPTED
        ).select_related('from_user', 'to_user')
        
        watched_users = {user}
        for f in friends:
            watched_users.add(f.to_user if f.from_user == user else f.from_user)
            
        # 2. Fetch all active stories for watched users in a single query
        active_stories = Story.objects.filter(
            user__in=watched_users,
            expires_at__gt=timezone.now()
        ).select_related('user').order_by('created_at')
        
        stories_by_user = defaultdict(list)
        for story in active_stories:
            stories_by_user[story.user_id].append(story)
            
        feed_data = []
        
        # Order chronologically or user-first
        sorted_users = sorted(list(watched_users), key=lambda u: (0 if u.id == user.id else 1, u.username))
        for w_user in sorted_users:
            user_stories = stories_by_user[w_user.id]
            if user_stories:
                feed_data.append({
                    "user_id": w_user.id,
                    "username": w_user.username,
                    "avatar": w_user.avatar.url if w_user.avatar else None,
                    "stories": StorySerializer(user_stories, many=True).data
                })
        
        return Response(feed_data, status=status.HTTP_200_OK)

class StoryDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, story_id):
        story = get_object_or_404(Story, id=story_id, user=request.user)
        story.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

from .models import StoryLike

class StoryLikeView(APIView):
    """Toggle like on a story."""
    permission_classes = [IsAuthenticated]

    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        like, created = StoryLike.objects.get_or_create(story=story, user=request.user)
        
        if not created:
            # Already liked, so unlike
            like.delete()
            return Response({"liked": False, "likes_count": story.likes.count()})
        
        return Response({"liked": True, "likes_count": story.likes.count()})
