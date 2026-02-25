from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Achievement
from rest_framework import serializers


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'name', 'description', 'icon', 'date_awarded', 'challenge']
        read_only_fields = fields


class AchievementListView(generics.ListAPIView):
    """List all achievements for the authenticated user."""
    permission_classes = [IsAuthenticated]
    serializer_class = AchievementSerializer

    def get_queryset(self):
        return Achievement.objects.filter(user=self.request.user).order_by('-date_awarded')
