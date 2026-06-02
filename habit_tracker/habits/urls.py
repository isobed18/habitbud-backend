#habits/urls.py

# we will use this file to define the urls for the habits app

from django.urls import path
from . import views

urlpatterns = [
    path('', views.HabitListView.as_view(), name='habit-list'),
    path('templates/', views.HabitTemplateListView.as_view(), name='habit-template-list'),
    path('connections/', views.HabitConnectionListView.as_view(), name='habit-connection-list'),
    path('connections/create/', views.HabitConnectionCreateView.as_view(), name='habit-connection-create'),
    path('connections/<uuid:connection_id>/respond/', views.HabitConnectionRespondView.as_view(), name='habit-connection-respond'),
    path('groups/', views.HabitGroupListView.as_view(), name='habit-group-list'),
    path('groups/create/', views.HabitGroupCreateView.as_view(), name='habit-group-create'),
    path('groups/<uuid:group_id>/leave/', views.HabitGroupLeaveView.as_view(), name='habit-group-leave'),
    path('rooms/<uuid:conversation_id>/recover-streak/', views.StreakRecoveryView.as_view(), name='streak-recovery'),
    path('rooms/<uuid:conversation_id>/reserve/', views.GroupReserveView.as_view(), name='group-reserve'),
    path('<uuid:habit_id>/', views.HabitDetailView.as_view(), name='habit-detail'),
    path('<uuid:habit_id>/stats/', views.HabitStatsView.as_view(), name='habit-stats'),
]