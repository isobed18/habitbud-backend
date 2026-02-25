from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .forms import CustomUserCreationForm
from .serializers import UserSerializer, UserRegistrationSerializer, ReminderSerializer, NotificationSerializer
from .models import Reminder, Notification
from django.db.models import Q

User = get_user_model()


class RegisterView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except KeyError:
            return Response({"error": "Missing 'refresh' token in request body."}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeaderboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from friends.models import Friendship

        friendships = Friendship.objects.filter(
            (Q(from_user=request.user) | Q(to_user=request.user)),
            status=Friendship.Status.ACCEPTED
        )
        
        friends = []
        for f in friendships:
            if f.from_user == request.user:
                friends.append(f.to_user)
            else:
                friends.append(f.from_user)
        
        users = list(friends) + [request.user]
        users.sort(key=lambda u: u.xp, reverse=True)
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class PublicUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from friends.models import Friendship
        from habits.models import Habit
        from habits.serializers import HabitSerializer

        target_user = get_object_or_404(User, id=user_id)
        
        is_friend = Friendship.objects.filter(
            (Q(from_user=request.user, to_user=target_user) | Q(from_user=target_user, to_user=request.user)),
            status=Friendship.Status.ACCEPTED
        ).exists()

        data = {
            "id": target_user.id,
            "username": target_user.username,
            "bio": target_user.bio,
            "level": target_user.level,
            "xp": target_user.xp,
            "points": target_user.points,
            "avatar": target_user.avatar.url if target_user.avatar else None,
            "is_friend": is_friend,
            "habits": []
        }

        if is_friend or request.user == target_user:
             habits = Habit.objects.filter(user=target_user)
             data["habits"] = HabitSerializer(habits, many=True).data

        return Response(data)


class CustomTokenRefreshView(TokenRefreshView):
    """Handle cases where the user associated with refresh token has been deleted."""
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            if "matching query does not exist" in str(e):
                return Response(
                    {"code": "user_not_found", "detail": "User no longer exists. Please login again."}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            raise e


# ============================================================================
# REMINDERS
# ============================================================================

class ReminderListView(generics.ListAPIView):
    """List all scheduled reminders for the user."""
    serializer_class = ReminderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Reminder.objects.filter(user=self.request.user).order_by('time')


class ReminderDeleteView(generics.DestroyAPIView):
    """Delete a reminder."""
    serializer_class = ReminderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Reminder.objects.filter(user=self.request.user)


# ============================================================================
# NOTIFICATIONS
# ============================================================================

class NotificationListView(generics.ListAPIView):
    """List notifications for the authenticated user."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class NotificationMarkReadView(APIView):
    """Mark a single notification as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'message': 'Notification marked as read.'})


class NotificationMarkAllReadView(APIView):
    """Mark all notifications as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': f'{count} notifications marked as read.'})


# ============================================================================
# USER SEARCH
# ============================================================================

class UserSearchView(APIView):
    """Search users by username (partial match)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'error': 'Search query must be at least 2 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = User.objects.filter(
            username__icontains=query
        ).exclude(id=request.user.id)[:20]
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)