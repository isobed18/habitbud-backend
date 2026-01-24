# habit_tracker/friends/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Friendship

User = get_user_model()

# A simple serializer for displaying user details in friend lists
class FriendUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'bio']

class FriendshipSerializer(serializers.ModelSerializer):
    # Use the simple user serializer for nested representation
    from_user = FriendUserSerializer(read_only=True)
    to_user = FriendUserSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'from_user', 'to_user', 'status', 'created_at', 'streak', 'last_interaction_date']
        read_only_fields = ['status', 'from_user', 'to_user', 'created_at', 'streak', 'last_interaction_date']