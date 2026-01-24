# chat/urls.py
from django.urls import path
from .views import (
    ConversationListView,
    MessageListView,
    MessageCreateView,
    StartConversationView,
    ProofSubmissionView,
    AIProofSubmissionView,
    VerifyProofView,
    AICoachView,
    AIAgentView,
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


    # Get all messages for a conversation and create a new message
    path('conversations/<uuid:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<uuid:conversation_id>/messages/create/', MessageCreateView.as_view(), name='message-create'),
    
    # Proof submission and verification
    path('proof/submit/', ProofSubmissionView.as_view(), name='proof-submit'), # Social Proof (Friends)
    path('proof/ai/', AIProofSubmissionView.as_view(), name='proof-ai'), # AI Proof (Solo)
    path('proof/<uuid:message_id>/verify/', VerifyProofView.as_view(), name='proof-verify'),
    path('ai-coach/', AICoachView.as_view(), name='ai-coach'),
    path('ai-agent/', AIAgentView.as_view(), name='ai-agent'),

    # Stories
    path('stories/create/', StoryCreateView.as_view(), name='story-create'),
    path('stories/feed/', StoryFeedView.as_view(), name='story-feed'),
    path('stories/<uuid:story_id>/like/', StoryLikeView.as_view(), name='story-like'),
    path('stories/<uuid:story_id>/delete/', StoryDeleteView.as_view(), name='story-delete'),
]