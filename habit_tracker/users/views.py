# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from rest_framework_simplejwt.exceptions import TokenError
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import UserSerializer
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.http import JsonResponse
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserRegistrationSerializer
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

   

class RegisterView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = []  # Login/Register için authentication gerekmez

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
    authentication_classes = []  # Login/Register için authentication gerekmez

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
            # Refresh anahtarı eksikse
            return Response({"error": "Missing 'refresh' token in request body."}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError as e:
            # Token geçersiz veya süresi dolduysa
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Diğer hatalar
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
        from django.db.models import Q

        # Get all accepted friendships for the current user
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
        
        # Include self
        users = list(friends) + [request.user]
        # Sort by XP descending
        users.sort(key=lambda u: u.xp, reverse=True)
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class PublicUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from friends.models import Friendship
        from django.db.models import Q
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
            "habits": [] # Show public habits if friends
        }

        if is_friend or request.user == target_user:
             habits = Habit.objects.filter(user=target_user)
             data["habits"] = HabitSerializer(habits, many=True).data

        return Response(data)

from rest_framework_simplejwt.views import TokenRefreshView
from django.shortcuts import get_object_or_404

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom view to handle cases where the user associated with the refresh token
    has been deleted (e.g., during development seeding), returning 401 instead of 500.
    """
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            # Catch "CustomUser matching query does not exist" or similar DB errors
            if "matching query does not exist" in str(e):
                return Response(
                    {"code": "user_not_found", "detail": "User no longer exists. Please login again."}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            raise e

from .models import Reminder
from .serializers import ReminderSerializer
from rest_framework import generics

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