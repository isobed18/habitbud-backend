# chat/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, ChatMessage, Story
from users.serializers import UserSerializer # Assuming you have a UserSerializer in your users app

class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    related_habit_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    related_habit = serializers.PrimaryKeyRelatedField(read_only=True)
    proof_image = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender', 'content', 'message_type', 'proof_image',
            'related_habit', 'related_habit_id', 'verification_status', 'created_at'
        ]
        read_only_fields = [
            'id', 'sender', 'message_type', 'verification_status', 'created_at', 'related_habit'
        ]

    def get_proof_image(self, obj):
        if obj.proof_image:
            return obj.proof_image.url
        return None

    def create(self, validated_data):
        related_habit_id = validated_data.pop('related_habit_id', None)
        if related_habit_id:
            from habits.models import Habit
            try:
                validated_data['related_habit'] = Habit.objects.get(id=related_habit_id)
                validated_data['message_type'] = ChatMessage.MessageType.PROOF
                validated_data['verification_status'] = ChatMessage.VerificationStatus.PENDING
            except Habit.DoesNotExist:
                pass
        return super().create(validated_data)

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    created_by_id = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'last_message', 'created_at',
            'name', 'is_group', 'avatar', 'display_name', 'created_by_id',
            'live_room_type', 'required_habit_slug', 'capacity', 'privacy',
            'join_policy', 'pomodoro_work_minutes', 'pomodoro_break_minutes',
        ]

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return ChatMessageSerializer(last_message).data
        return None

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_display_name(self, obj):
        """Group rooms use their name; DMs show the *other* participant."""
        if obj.is_group:
            return obj.name or 'Group'
        request = self.context.get('request')
        me = getattr(request, 'user', None)
        others = [p for p in obj.participants.all() if p != me]
        if others:
            return others[0].username
        return 'Chat'

    def get_created_by_id(self, obj):
        return str(obj.created_by_id) if obj.created_by_id else None

class StorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_expired = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    habit_details = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            'id', 'user', 'habit', 'habit_details', 'image', 'content', 
            'created_at', 'expires_at', 'is_expired', 'likes_count', 'is_liked'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'expires_at']

    def get_is_expired(self, obj):
        from django.utils import timezone
        return obj.expires_at < timezone.now()

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_habit_details(self, obj):
        if obj.habit:
            return {
                "id": obj.habit.id,
                "name": obj.habit.name,
                "icon": obj.habit.icon if hasattr(obj.habit, 'icon') else None
            }
        return None
