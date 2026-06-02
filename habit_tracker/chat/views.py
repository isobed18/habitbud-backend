# chat/views.py
import json
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from .models import Conversation, ChatMessage
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

        room = Conversation.objects.create(name=name, is_group=True, created_by=request.user)
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
                room.participants.add(friend)

        serializer = ConversationSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoomMembershipView(APIView):
    """Join (POST) or leave (DELETE) a group chat room."""
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id, *args, **kwargs):
        room = get_object_or_404(Conversation, id=conversation_id, is_group=True)
        room.participants.add(request.user)
        return Response(ConversationSerializer(room, context={'request': request}).data)

    def delete(self, request, conversation_id, *args, **kwargs):
        room = get_object_or_404(Conversation, id=conversation_id, is_group=True)
        room.participants.remove(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        if not habit.is_completed_today():
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
        # Without this, repeated 'verify' calls would award XP/diamonds each time.
        if proof_message.verification_status != ChatMessage.VerificationStatus.PENDING:
            return Response({'error': 'Bu check zaten işlendi.'}, status=status.HTTP_409_CONFLICT)

        reward_info = {}
        if action == 'verify':
            habit = proof_message.related_habit
            if habit:
                # STRICT CHECK: Habit must be completed today to accept verification
                if not habit.is_completed_today():
                    return Response({'error': 'Habit is not completed today. Cannot verify.'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Update Verification Streak & Stats (this is the ONLY place it should be called)
                habit.update_verification_streak()
                
            proof_message.verification_status = ChatMessage.VerificationStatus.VERIFIED
            
            # Get friendship for streak multiplier
            from users.gamification import GamificationEngine
            from users.services import UserService
            
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
                print(f"Error updating friendship streak: {e}")

            # SENDER: base_verify × habit_streak_mult × friend_streak_mult
            habit_streak = habit.verification_streak if habit else 0
            sender_xp, h_mult, f_mult = GamificationEngine.calculate_full_reward(
                GamificationEngine.BASE_VERIFY_XP, habit_streak, friend_streak
            )
            UserService.add_xp(proof_message.sender, sender_xp)
            
            # Award points (diamonds) decoupled from XP
            UserService.add_points(proof_message.sender, 1)
            UserService.add_points(request.user, 1)

            # VERIFIER: base_verifier × friend_streak_mult
            verifier_xp = int(round(GamificationEngine.BASE_VERIFIER_XP *
                            GamificationEngine.calculate_friend_streak_multiplier(friend_streak)))
            UserService.add_xp(request.user, verifier_xp)

            is_milestone = bool(habit and GamificationEngine.is_milestone(habit_streak))
            milestone_bonus = 0
            if is_milestone:
                milestone_bonus = habit_streak * 2
                UserService.add_points(proof_message.sender, milestone_bonus)

            # Tell the sender their check was approved, and celebrate milestones.
            from users.notifications import notify
            habit_name = habit.name if habit else 'alışkanlık'
            notify(
                proof_message.sender,
                "Check'in onaylandı! 🔥",
                f"{request.user.username}, {habit_name} check'ini onayladı. +{sender_xp} XP ve +1 💎 kazandın!",
                ntype='CHECK',
                data={'habit_id': str(habit.id) if habit else None, 'xp': sender_xp, 'points': 1},
            )
            if is_milestone:
                tier, tier_name = GamificationEngine.get_streak_tier(habit_streak)
                notify(
                    proof_message.sender,
                    f"{habit_streak} günlük seri! 🔥",
                    f"{habit_name}: üst üste {habit_streak} gün. {tier_name} seviyesine ulaştın! Ekstra +{milestone_bonus} 💎 kazandın!",
                    ntype='STREAK',
                    data={'habit_id': str(habit.id), 'streak': habit_streak, 'tier': tier, 'points_bonus': milestone_bonus},
                )

            reward_info = {
                'sender_xp': sender_xp,
                'verifier_xp': verifier_xp,
                'sender_diamonds': 1 + milestone_bonus,
                'verifier_diamonds': 1,
                'habit_multiplier': h_mult,
                'friend_multiplier': f_mult,
                'habit_streak': habit_streak,
                'friend_streak': friend_streak,
                'milestone': is_milestone,
                'milestone_bonus': milestone_bonus,
            }

        else:
            proof_message.verification_status = ChatMessage.VerificationStatus.REJECTED

        proof_message.save(update_fields=['verification_status'])
        self.broadcast_verification(proof_message)

        return Response(
            {**ChatMessageSerializer(proof_message).data, **reward_info},
            status=status.HTTP_200_OK,
        )

    def broadcast_verification(self, message):
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
