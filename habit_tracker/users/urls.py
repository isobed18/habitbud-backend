from django.urls import path
from . import views
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

    # Notifications
    path('api/notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('api/notifications/<uuid:notification_id>/read/', views.NotificationMarkReadView.as_view(), name='notification-read'),
    path('api/notifications/read-all/', views.NotificationMarkAllReadView.as_view(), name='notification-read-all'),

    # Shortcuts
    path('friends/', FriendListView.as_view(), name='user-friends-alias'),
    path('items/', UserInventoryView.as_view(), name='user-items'),
    path('reminders/', views.ReminderListView.as_view(), name='user-reminders'),
    path('reminders/<uuid:pk>/', views.ReminderDeleteView.as_view(), name='user-reminder-delete'),
]
