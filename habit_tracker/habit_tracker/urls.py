"""
URL configuration for habit_tracker project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'habitbud-backend'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('users/', include('users.urls')),
    path('habits/', include('habits.urls')),
    path('friends/', include('friends.urls')),
    path('chat/', include('chat.urls')),
    path('challenges/', include('challange.urls')),
    path('achievements/', include('achievement.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
