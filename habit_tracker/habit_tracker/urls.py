"""
URL configuration for habit_tracker project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as media_serve
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

# Serve user-uploaded media. In dev via the static helper; in production via the
# static serve view (fine for MVP scale — move to nginx/S3/CDN as you grow).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
