# chat/urls.py
from django.urls import path
from .views import (
    ConversationListView,
    MessageListView,
    MessageCreateView,
    StartConversationView,
    CreateRoomView,
    RoomMembershipView,
    ProofSubmissionView,
    VerifyProofView,
    StoryCreateView,
    StoryFeedView,
    StoryLikeView,
    StoryDeleteView,
)

urlpatterns = [
    # Get a list of all conversations for the user
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    # Start or find a conversation with a user
    path('conversations/start/', StartConversationView.as_view(), name='start-conversation'),

    # Group chat rooms
    path('rooms/', CreateRoomView.as_view(), name='room-create'),
    path('rooms/<uuid:conversation_id>/membership/', RoomMembershipView.as_view(), name='room-membership'),

    # Get all messages for a conversation and create a new message
    path('conversations/<uuid:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<uuid:conversation_id>/messages/create/', MessageCreateView.as_view(), name='message-create'),

    # Check submission and verification (a "check" = a habit proof snap sent to friends)
    path('checks/submit/', ProofSubmissionView.as_view(), name='check-submit'),
    path('checks/<uuid:message_id>/verify/', VerifyProofView.as_view(), name='check-verify'),
    # Backwards-compatible aliases (old "proof" naming)
    path('proof/submit/', ProofSubmissionView.as_view(), name='proof-submit'),
    path('proof/<uuid:message_id>/verify/', VerifyProofView.as_view(), name='proof-verify'),

    # Stories
    path('stories/create/', StoryCreateView.as_view(), name='story-create'),
    path('stories/feed/', StoryFeedView.as_view(), name='story-feed'),
    path('stories/<uuid:story_id>/like/', StoryLikeView.as_view(), name='story-like'),
    path('stories/<uuid:story_id>/delete/', StoryDeleteView.as_view(), name='story-delete'),
]
