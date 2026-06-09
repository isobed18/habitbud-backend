from rest_framework import serializers
from .models import Item, UserItem, ChallengeTemplate, Challenge
from users.serializers import UserSerializer

# Which avatar socket (Empty in the GLB) an item's anchor maps to in the viewer.
ANCHOR_SOCKET = {
    'hand': 'socket_r',
    'head': 'socket_head',
    'face': 'socket_head',
    'neck': 'socket_head',
    'back': 'socket_back',
    'none': None,
}


class ItemSerializer(serializers.ModelSerializer):
    model_glb = serializers.SerializerMethodField()
    socket = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ['id', 'name', 'slug', 'description', 'image', 'rarity',
                  'model_glb', 'model_url', 'anchor', 'item_scale', 'socket',
                  'is_shop_item', 'price_points', 'shop_sort']

    def get_model_glb(self, obj):
        if obj.model_glb:
            try:
                return obj.model_glb.url
            except Exception:
                return None
        return None

    def get_socket(self, obj):
        return ANCHOR_SOCKET.get(obj.anchor, 'socket_r')

class ChallengeTemplateSerializer(serializers.ModelSerializer):
    reward_item = ItemSerializer(read_only=True)
    active_participants = serializers.SerializerMethodField()
    total_participants = serializers.SerializerMethodField()
    my_status = serializers.SerializerMethodField()
    my_completed_date = serializers.SerializerMethodField()

    class Meta:
        model = ChallengeTemplate
        fields = [
            'id', 'name', 'description', 'predefined_habit_name',
            'challenge_type', 'duration_days', 'reward_xp',
            'reward_points', 'reward_item', 'active_participants', 'total_participants',
            'my_status', 'my_completed_date'
        ]

    def _my_participation(self, obj):
        from django.db.models import Q
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        return obj.participations.filter(
            Q(creator=request.user) | Q(partner=request.user)
        ).order_by('-start_date').first()

    def get_my_status(self, obj):
        p = self._my_participation(obj)
        return p.status if p else None

    def get_my_completed_date(self, obj):
        p = self._my_participation(obj)
        if p and p.status == 'COMPLETED':
            return p.last_update_date or p.start_date
        return None

    def get_active_participants(self, obj):
        return obj.participations.filter(status='ACTIVE').count()

    def get_total_participants(self, obj):
        # Everyone who ever joined (excludes rejected/withdrawn invites).
        return obj.participations.exclude(status='REJECTED').count()

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
