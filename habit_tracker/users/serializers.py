from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'bio', 'xp', 'level', 'points', 'avatar',
                  'avatar_config', 'region', 'is_private', 'message_privacy', 'streak_freezes')
        read_only_fields = ('id', 'xp', 'level', 'points', 'streak_freezes')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'bio')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

from .models import Reminder, Notification, AvatarModel


class AvatarModelSerializer(serializers.ModelSerializer):
    glb = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = AvatarModel
        fields = ['id', 'slug', 'name', 'emoji', 'glb', 'glb_url', 'thumbnail', 'scale']

    def get_glb(self, obj):
        if obj.glb:
            try:
                return obj.glb.url
            except Exception:
                return None
        return None

    def get_thumbnail(self, obj):
        if obj.thumbnail:
            try:
                return obj.thumbnail.url
            except Exception:
                return None
        return None

class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ['id', 'title', 'message', 'time', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'created_at']