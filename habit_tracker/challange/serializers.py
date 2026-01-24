from rest_framework import serializers
from .models import Item, UserItem, ChallengeTemplate, Challenge
from users.serializers import UserSerializer

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'name', 'description', 'image', 'rarity']

class ChallengeTemplateSerializer(serializers.ModelSerializer):
    reward_item = ItemSerializer(read_only=True)
    active_participants = serializers.SerializerMethodField()

    class Meta:
        model = ChallengeTemplate
        fields = [
            'id', 'name', 'description', 'predefined_habit_name', 
            'challenge_type', 'duration_days', 'reward_xp', 
            'reward_points', 'reward_item', 'active_participants'
        ]

    def get_active_participants(self, obj):
        return obj.participations.filter(status='ACTIVE').count()

class ChallengeSerializer(serializers.ModelSerializer):
    template = ChallengeTemplateSerializer(read_only=True)
    creator = UserSerializer(read_only=True)
    partner = UserSerializer(read_only=True)
    waiting_for_me = serializers.SerializerMethodField()
    name = serializers.CharField(source='template.name', read_only=True)
    description = serializers.CharField(source='template.description', read_only=True)
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'name', 'description', 'template', 'creator', 'partner', 'habit_name', 
            'current_streak', 'start_date', 'status', 'waiting_for_me',
            'creator_completed_today', 'partner_completed_today',
            'creator_verified_partner', 'partner_verified_creator'
        ]
        read_only_fields = ['id', 'current_streak', 'start_date', 'status', 'habit_name', 'waiting_for_me']

    def get_waiting_for_me(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return False
        # If Pending and I am the partner, then it's waiting for ME to accept
        return obj.status == 'PENDING' and obj.partner == request.user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Hide partner for SOLO challenges as requested
        if instance.template.challenge_type == 'SOLO':
            data.pop('partner', None)
        return data
