# habit_tracker/friends/views.py

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import Friendship
from .serializers import FriendshipSerializer, FriendUserSerializer
from django.db.models import Q

User = get_user_model()

class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        to_user_username = request.data.get('username')
        if not to_user_username:
            return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            to_user = User.objects.get(username=to_user_username)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        from_user = request.user
        
        if from_user == to_user:
            return Response({'error': 'You cannot send a friend request to yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if a request already exists
        if Friendship.objects.filter(from_user=from_user, to_user=to_user).exists() or \
           Friendship.objects.filter(from_user=to_user, to_user=from_user).exists():
            return Response({'error': 'A friend request already exists between you and this user.'}, status=status.HTTP_400_BAD_REQUEST)

        friend_request = Friendship.objects.create(from_user=from_user, to_user=to_user)
        serializer = FriendshipSerializer(friend_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FriendRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendshipSerializer

    def get_queryset(self):
        # Return pending requests received by the current user
        return Friendship.objects.filter(to_user=self.request.user, status=Friendship.Status.PENDING)

class RespondToFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id, *args, **kwargs):
        try:
            friend_request = Friendship.objects.get(id=request_id, to_user=request.user)
        except Friendship.DoesNotExist:
            return Response({'error': 'Friend request not found.'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action') # 'accept' or 'decline'

        if friend_request.status != Friendship.Status.PENDING:
            return Response({'error': 'This request has already been responded to.'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'accept':
            friend_request.status = Friendship.Status.ACCEPTED
            friend_request.save()
            return Response({'message': 'Friend request accepted.'}, status=status.HTTP_200_OK)
        elif action == 'decline':
            friend_request.status = Friendship.Status.DECLINED
            friend_request.save() 
            return Response({'message': 'Friend request declined.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)


class FriendRemoveView(APIView):
    """Remove an accepted friendship."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, friend_id, *args, **kwargs):
        friendship = Friendship.objects.filter(
            (Q(from_user=request.user, to_user_id=friend_id) |
             Q(from_user_id=friend_id, to_user=request.user)),
            status=Friendship.Status.ACCEPTED
        ).first()

        if not friendship:
            return Response({'error': 'Friendship not found.'}, status=status.HTTP_404_NOT_FOUND)

        friendship.delete()
        return Response({'message': 'Friend removed.'}, status=status.HTTP_200_OK)


class FriendListView(generics.ListAPIView):
    """List all accepted friends with friendship streak info."""
    permission_classes = [IsAuthenticated]
    serializer_class = FriendUserSerializer

    def get_queryset(self):
        user = self.request.user
        friendships = Friendship.objects.filter(
            Q(from_user=user, status=Friendship.Status.ACCEPTED) |
            Q(to_user=user, status=Friendship.Status.ACCEPTED)
        )
        
        friend_ids = []
        for friendship in friendships:
            if friendship.from_user_id == user.id:
                friend_ids.append(friendship.to_user_id)
            else:
                friend_ids.append(friendship.from_user_id)
                
        return User.objects.filter(id__in=friend_ids)

    def list(self, request, *args, **kwargs):
        """Override to include streak data per friend."""
        queryset = self.get_queryset()
        user = request.user

        friends_data = []
        for friend in queryset:
            friendship = Friendship.objects.filter(
                (Q(from_user=user, to_user=friend) | Q(from_user=friend, to_user=user)),
                status=Friendship.Status.ACCEPTED
            ).first()

            friend_data = FriendUserSerializer(friend).data
            friend_data['friendship_streak'] = friendship.streak if friendship else 0
            friend_data['last_interaction_date'] = friendship.last_interaction_date if friendship else None
            friends_data.append(friend_data)

        return Response(friends_data)