#habits/urls.py

# we will use this file to define the urls for the habits app

from django.urls import path
from . import views

urlpatterns = [
    path('', views.HabitListView.as_view(), name='habit-list'),
    path('templates/', views.HabitTemplateListView.as_view(), name='habit-template-list'),
    path('<uuid:habit_id>/', views.HabitDetailView.as_view(), name='habit-detail'),
    path('<uuid:habit_id>/stats/', views.HabitStatsView.as_view(), name='habit-stats'),
]