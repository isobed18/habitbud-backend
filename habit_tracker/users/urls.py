from django.urls import path
from . import views
from . import auth_extras
from friends.views import FriendListView
from rest_framework_simplejwt.views import TokenRefreshView
from challange.views import UserInventoryView

urlpatterns = [
    path('api/register/', views.RegisterView.as_view(), name='register'),
    path('api/login/', views.LoginView.as_view(), name='login'),
    path('api/token/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/profile/', views.UserProfileView.as_view(), name='profile'),
    path('api/leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('api/profile/<uuid:user_id>/', views.PublicUserProfileView.as_view(), name='public-profile'),
    path('api/search/', views.UserSearchView.as_view(), name='user-search'),

    # Blocking
    path('api/blocks/', views.BlockListView.as_view(), name='block-list'),
    path('api/blocks/<uuid:user_id>/', views.BlockView.as_view(), name='block-user'),

    # Notifications
    path('api/notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('api/notifications/<uuid:notification_id>/read/', views.NotificationMarkReadView.as_view(), name='notification-read'),
    path('api/notifications/read-all/', views.NotificationMarkAllReadView.as_view(), name='notification-read-all'),

    # Push notifications (Expo)
    path('api/push-token/', views.PushTokenView.as_view(), name='push-token'),

    # 3D avatar base models (for Avatar Studio)
    path('api/avatar-models/', views.AvatarModelListView.as_view(), name='avatar-models'),
    path('api/combos/', views.CombosView.as_view(), name='avatar-item-combos'),
    path('api/verify-purchase/', views.VerifyPurchaseView.as_view(), name='verify-purchase'),
    path('api/attach-tuning/', views.AttachTuningView.as_view(), name='attach-tuning'),
    path('api/stats/', views.UserStatsView.as_view(), name='user-stats'),

    # Auth extensions: e-mail verification + social sign-in
    path('api/email/send-verification/', auth_extras.SendEmailVerificationView.as_view(), name='email-send-verification'),
    path('api/email/verify/', auth_extras.VerifyEmailView.as_view(), name='email-verify'),
    path('api/auth/google/', auth_extras.GoogleAuthView.as_view(), name='auth-google'),
    path('api/auth/apple/', auth_extras.AppleAuthView.as_view(), name='auth-apple'),
    path('api/buy-freeze/', views.BuyStreakFreezeView.as_view(), name='buy-freeze'),

    # Shortcuts
    path('friends/', FriendListView.as_view(), name='user-friends-alias'),
    path('items/', UserInventoryView.as_view(), name='user-items'),
    path('reminders/', views.ReminderListView.as_view(), name='user-reminders'),
    path('reminders/<uuid:pk>/', views.ReminderDeleteView.as_view(), name='user-reminder-delete'),
]
