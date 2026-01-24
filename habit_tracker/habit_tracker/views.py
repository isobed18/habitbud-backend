from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime
from django.contrib.auth import logout
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from habits.forms import HabitForm
from django.contrib import messages
from habits.models import Habit
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from datetime import date
from rest_framework import status
from rest_framework.views import APIView
from django.core.cache import cache





def home(request):
    if request.user.is_authenticated:
        habits = Habit.objects.filter(user=request.user)  # Kullanıcının alışkanlıklarını al
    else:
        habits = []
    return render(request, 'home.html', {'habits': habits})
    
    


def get_server_time(request):
    server_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    return JsonResponse({'message': f'Server zamanı: {server_time}'})


