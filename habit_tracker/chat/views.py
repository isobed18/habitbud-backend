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

        is_friend = Friendship.objects.filter(
            (Q(from_user=user, to_user=target_user) | Q(from_user=target_user, to_user=user)),
            status=Friendship.Status.ACCEPTED
        ).exists()

        if not is_friend:
            return Response({'error': 'You can only start conversations with friends.'}, status=status.HTTP_403_FORBIDDEN)

        conversation = Conversation.objects.annotate(participant_count=Count('participants')).filter(
            participants=user
        ).filter(
            participants=target_user
        ).filter(
            participant_count=2
        ).first()

        if conversation:
            serializer = ConversationSerializer(conversation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            new_conversation = Conversation.objects.create()
            new_conversation.participants.add(user, target_user)
            serializer = ConversationSerializer(new_conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.conversations.all().distinct()

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

        self.broadcast_proof_message(proof_message)
        return Response(ChatMessageSerializer(proof_message).data, status=status.HTTP_201_CREATED)

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

class AIProofSubmissionView(APIView):
    """AI Proof - Currently shelved. Will return 503."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return Response(
            {'error': 'AI proof verification is currently unavailable. Please use social proof with friends.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class VerifyProofView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id, *args, **kwargs):
        action = request.data.get('action')
        if action not in ['verify', 'reject']:
            return Response({'error': "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        proof_message = get_object_or_404(ChatMessage, id=message_id, message_type=ChatMessage.MessageType.PROOF)
        
        if request.user == proof_message.sender:
            return Response({'error': 'Cannot verify own proof.'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user not in proof_message.conversation.participants.all():
            return Response({'error': 'Not a participant.'}, status=status.HTTP_403_FORBIDDEN)

        if action == 'verify':
            habit = proof_message.related_habit
            if habit:
                # STRICT CHECK: Habit must be completed today to accept verification
                if not habit.is_completed_today():
                    return Response({'error': 'Habit is not completed today. Cannot verify.'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Update Verification Streak & Stats
                habit.update_verification_streak()
                
            proof_message.verification_status = ChatMessage.VerificationStatus.VERIFIED
            
            # Award XP to the sender
            from users.services import UserService
            UserService.add_xp(proof_message.sender, 50)
                
            # Update Friendship Streak
            try:
                friendship = Friendship.objects.filter(
                    (Q(from_user=request.user, to_user=proof_message.sender) | 
                     Q(from_user=proof_message.sender, to_user=request.user)),
                    status=Friendship.Status.ACCEPTED
                ).first()
                if friendship:
                    friendship.update_streak()
            except Exception as e:
                print(f"Error updating friendship streak: {e}")

        else:
            proof_message.verification_status = ChatMessage.VerificationStatus.REJECTED
        
        proof_message.save(update_fields=['verification_status'])
        self.broadcast_verification(proof_message)
        
        return Response(ChatMessageSerializer(proof_message).data, status=status.HTTP_200_OK)

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

class AICoachView(APIView):
    """AI Coach - Currently shelved. Will return 503."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return Response(
            {'error': 'AI coaching is currently unavailable.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class AIAgentView(APIView):
    """AI Agent - Currently shelved. Will return 503."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return Response(
            {'error': 'AI agent is currently unavailable.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
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
        user = self.request.user
        
        # 1. Provide a list of "users to watch" (Friends + Self)
        friends = Friendship.objects.filter(
            (Q(from_user=user) | Q(to_user=user)),
            status=Friendship.Status.ACCEPTED
        )
        
        watched_users = {user}
        for f in friends:
            watched_users.add(f.to_user if f.from_user == user else f.from_user)
            
        feed_data = []
        
        for watched_user in watched_users:
            active_stories = Story.objects.filter(
                user=watched_user,
                expires_at__gt=timezone.now()
            ).order_by('created_at') # Oldest first for chronological viewing
            
            if active_stories.exists():
                feed_data.append({
                    "user_id": watched_user.id,
                    "username": watched_user.username,
                    "avatar": watched_user.avatar.url if watched_user.avatar else None,
                    "stories": StorySerializer(active_stories, many=True).data
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
