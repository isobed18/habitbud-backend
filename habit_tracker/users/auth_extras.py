"""Auth extensions: e-mail verification + Google / Apple sign-in.

E-mail verification uses Django's cryptographic signing (no DB table): we mail a
signed token; hitting /verify/ with it flips user.email_verified. In dev the
mail prints to the console (EMAIL_BACKEND default).

Google sign-in is fully implemented via Google's tokeninfo endpoint (no extra
dependency): the app obtains an id_token (expo-auth-session / Google SDK) and
POSTs it here; we validate audience + issuer, find-or-create the user, and
return our JWT pair. Apple is scaffolded: it requires verifying the
identity_token against Apple's JWKS — wire it when the Apple dev account is set
up (TODOs inline).
"""
import logging
import os

import requests
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
logger = logging.getLogger('habit_tracker')

EMAIL_TOKEN_SALT = 'habitbud.email-verify'
EMAIL_TOKEN_MAX_AGE = 60 * 60 * 48  # 48h


def _jwt_for(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class SendEmailVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.email:
            return Response({'error': 'Hesapta e-posta yok.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.email_verified:
            return Response({'status': 'already_verified'})
        token = signing.dumps({'uid': str(user.id), 'email': user.email}, salt=EMAIL_TOKEN_SALT)
        base = os.getenv('PUBLIC_API_URL', 'http://192.168.1.8:8000').rstrip('/')
        link = f'{base}/users/api/email/verify/?token={token}'
        send_mail(
            'HabitBud — e-posta doğrulama',
            f'Merhaba {user.username}! E-postanı doğrulamak için: {link}\n(48 saat geçerli)',
            os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@habitbud.app'),
            [user.email],
            fail_silently=False,
        )
        return Response({'status': 'sent'})


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('token', '')
        try:
            data = signing.loads(token, salt=EMAIL_TOKEN_SALT, max_age=EMAIL_TOKEN_MAX_AGE)
        except signing.SignatureExpired:
            return Response({'error': 'Bağlantının süresi dolmuş.'}, status=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return Response({'error': 'Geçersiz doğrulama bağlantısı.'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=data['uid'], email=data['email']).first()
        if not user:
            return Response({'error': 'Kullanıcı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        return Response({'status': 'verified', 'username': user.username})


class GoogleAuthView(APIView):
    """POST { "id_token": "..." } -> our JWT pair (sign-in or sign-up)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
        if not client_id:
            return Response({'error': 'google_auth_unconfigured'},
                            status=status.HTTP_501_NOT_IMPLEMENTED)
        id_token = request.data.get('id_token', '')
        if not id_token:
            return Response({'error': 'id_token required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            resp = requests.get('https://oauth2.googleapis.com/tokeninfo',
                                params={'id_token': id_token}, timeout=10)
            info = resp.json()
        except Exception:
            return Response({'error': 'google_unreachable'}, status=status.HTTP_502_BAD_GATEWAY)
        if resp.status_code != 200 or info.get('aud') != client_id or \
                info.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
            return Response({'error': 'invalid_google_token'}, status=status.HTTP_401_UNAUTHORIZED)

        email = info.get('email', '')
        if not email or info.get('email_verified') not in ('true', True):
            return Response({'error': 'google_email_unverified'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email).first()
        created = False
        if not user:
            base = email.split('@')[0][:24] or 'user'
            username, i = base, 1
            while User.objects.filter(username=username).exists():
                i += 1; username = f'{base}{i}'
            user = User.objects.create_user(username=username, email=email)
            user.set_unusable_password()
            created = True
        if not user.email_verified:
            user.email_verified = True
        user.save()
        from .serializers import UserSerializer
        return Response({'user': UserSerializer(user).data, 'created': created, **_jwt_for(user)})


class AppleAuthView(APIView):
    """POST { "identity_token": "...", "full_name": "..." } -> JWT pair.

    TODO to enable (needs the Apple developer account):
      1. Set APPLE_BUNDLE_ID in .env (e.g. com.isobed18.habitbud).
      2. Verify identity_token signature against Apple's JWKS
         (https://appleid.apple.com/auth/keys) with PyJWT[crypto]:
         jwt.decode(token, key, algorithms=['RS256'], audience=APPLE_BUNDLE_ID,
                    issuer='https://appleid.apple.com')
      3. Then mirror GoogleAuthView's find-or-create + _jwt_for flow using the
         'sub' (stable Apple user id) and optional 'email' claims.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not os.getenv('APPLE_BUNDLE_ID'):
            return Response({'error': 'apple_auth_unconfigured'},
                            status=status.HTTP_501_NOT_IMPLEMENTED)
        return Response({'error': 'apple_auth_not_implemented'},
                        status=status.HTTP_501_NOT_IMPLEMENTED)
