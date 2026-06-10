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

        scope = request.query_params.get('scope', 'friends')

        if scope == 'global':
            users = list(User.objects.order_by('-xp', 'username')[:50])
        elif scope == 'region':
            region = (request.user.region or '').strip()
            if region:
                users = list(User.objects.filter(region__iexact=region).order_by('-xp', 'username')[:50])
            else:
                users = [request.user]  # no region set yet
        else:  # friends (default): accepted friends + self
            friendships = Friendship.objects.filter(
                (Q(from_user=request.user) | Q(to_user=request.user)),
                status=Friendship.Status.ACCEPTED
            ).select_related('from_user', 'to_user')
            friends = []
            for f in friendships:
                friends.append(f.to_user if f.from_user == request.user else f.from_user)
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
            "avatar_config": target_user.avatar_config,
            "is_friend": is_friend,
            "is_private": target_user.is_private,
            "region": target_user.region,
            "habits": []
        }

        # Private profiles only reveal habits/stats to friends (or self).
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


class PushTokenView(APIView):
    """Register (or refresh) the caller's Expo push token.

    POST { "token": "ExponentPushToken[...]", "platform": "ios|android|web" }
    DELETE { "token": "..." } to unregister (e.g. on logout).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .models import DeviceToken
        token = (request.data.get('token') or '').strip()
        platform = request.data.get('platform', 'android')
        if not token:
            return Response({'error': 'token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # A token is unique to one device; reassign it to the current user.
        DeviceToken.objects.update_or_create(
            token=token,
            defaults={'user': request.user, 'platform': platform},
        )
        return Response({'status': 'registered'}, status=status.HTTP_200_OK)

    def delete(self, request):
        from .models import DeviceToken
        token = (request.data.get('token') or '').strip()
        if token:
            DeviceToken.objects.filter(token=token, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        
        from .models import Block
        blocked_ids = list(Block.objects.filter(
            Q(blocker=request.user) | Q(blocked=request.user)
        ).values_list('blocker_id', 'blocked_id'))
        exclude_ids = {request.user.id}
        for a, b in blocked_ids:
            exclude_ids.add(a); exclude_ids.add(b)

        users = User.objects.filter(
            username__icontains=query
        ).exclude(id__in=exclude_ids)[:20]

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class AvatarModelListView(APIView):
    """List active 3D avatar base models for the Avatar Studio."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import AvatarModel
        from .serializers import AvatarModelSerializer
        qs = AvatarModel.objects.filter(is_active=True)
        return Response(AvatarModelSerializer(qs, many=True, context={'request': request}).data)


class VerifyPurchaseView(APIView):
    """Verify a store purchase server-side and mark the user as paid.

    POST body:
      apple:  { "provider": "apple",  "receipt": "<base64 receipt>" }
      google: { "provider": "google", "product_id": "...", "purchase_token": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.utils import timezone
        from .models import Purchase
        from . import payments

        provider = request.data.get('provider', '')
        result = payments.verify(
            provider,
            receipt=request.data.get('receipt'),
            product_id=request.data.get('product_id'),
            purchase_token=request.data.get('purchase_token'),
        )
        if not result.ok:
            return Response({'verified': False, 'error': result.error},
                            status=status.HTTP_400_BAD_REQUEST)

        purchase, _ = Purchase.objects.update_or_create(
            transaction_id=result.transaction_id,
            defaults={
                'user': request.user,
                'provider': provider,
                'product_id': result.product_id or request.data.get('product_id', ''),
                'status': 'verified',
                'raw_response': result.raw,
                'verified_at': timezone.now(),
            },
        )
        if not request.user.is_paid:
            request.user.is_paid = True
            request.user.save(update_fields=['is_paid'])
        return Response({'verified': True, 'is_paid': True,
                         'product_id': purchase.product_id,
                         'transaction_id': purchase.transaction_id})


class CombosView(APIView):
    """Pre-baked combined avatar+item GLBs (media/models/combos/<avatar>__<item>.glb),
    used as preview/fallback. Returns a map { '<avatarbase>__<itemslug>': url }."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import os
        import re
        from django.conf import settings
        from django.core.cache import cache
        cached = cache.get('combo_glb_map')
        if cached is not None:
            return Response(cached)
        folder = os.path.join(settings.MEDIA_ROOT, 'models', 'combos')
        out = {}
        if os.path.isdir(folder):
            base_url = settings.MEDIA_URL.rstrip('/') + '/models/combos/'
            for f in os.listdir(folder):
                if not (f.lower().endswith('.glb') and '__' in f):
                    continue
                stem = os.path.splitext(f)[0].lower()
                av, item = stem.split('__', 1)
                # Normalize the avatar part to its base ('bear_socketed' -> 'bear')
                # so the key matches avatar.base + '__' + item.slug from the API.
                av = re.sub(r'[^a-z]', '', av.replace('socketed', ''))
                out[f"{av}__{item}"] = request.build_absolute_uri(base_url + f)
        cache.set('combo_glb_map', out, 300)  # filesystem scan, content rarely changes
        return Response(out)


class BlockListView(APIView):
    """List users the current user has blocked."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import Block
        blocked = User.objects.filter(blocked_by__blocker=request.user)
        return Response(UserSerializer(blocked, many=True).data)


class BlockView(APIView):
    """Block (POST) or unblock (DELETE) a user. Blocking also removes any
    existing friendship between the two users."""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        from .models import Block
        from friends.models import Friendship
        if str(user_id) == str(request.user.id):
            return Response({'error': 'Cannot block yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        target = get_object_or_404(User, id=user_id)
        Block.objects.get_or_create(blocker=request.user, blocked=target)
        # Drop any friendship in either direction.
        Friendship.objects.filter(
            (Q(from_user=request.user, to_user=target) | Q(from_user=target, to_user=request.user))
        ).delete()
        return Response({'status': 'blocked'})

    def delete(self, request, user_id):
        from .models import Block
        Block.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BuyStreakFreezeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        cost = 20
        if user.points < cost:
            return Response({'error': 'Yetersiz elmas. Seri Dondurucu satın almak için 20 elmas gerekiyor.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.points -= cost
        user.streak_freezes += 1
        user.save(update_fields=['points', 'streak_freezes'])
        
        return Response({
            'message': 'Seri Dondurucu başarıyla satın alındı! ❄️',
            'points': user.points,
            'streak_freezes': user.streak_freezes
        }, status=status.HTTP_200_OK)