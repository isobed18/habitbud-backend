# habit_tracker/friends/urls.py

from django.urls import path
from .views import (
    FriendRequestView,
    FriendRequestListView,
    RespondToFriendRequestView,
    FriendListView,
    FriendRemoveView,
)

urlpatterns = [
    # Send a friend request
    path('request/', FriendRequestView.as_view(), name='friend-request'),
    
    # Accept or decline a friend request
    path('requests/<uuid:request_id>/respond/', RespondToFriendRequestView.as_view(), name='friend-request-respond'),
    
    # List pending requests received by the user
    path('requests/pending/', FriendRequestListView.as_view(), name='friend-requests-pending'),
    
    # List all accepted friends (with streak info)
    path('list/', FriendListView.as_view(), name='friend-list'),

    # Remove a friend
    path('remove/<uuid:friend_id>/', FriendRemoveView.as_view(), name='friend-remove'),
]