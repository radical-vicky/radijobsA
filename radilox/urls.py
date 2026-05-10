from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('home.urls')),
    path('dashboard/', include('accounts.urls')),
    path('jobs/', include('jobs.urls')),
    path('applications/', include('application.urls')),
    # path('quiz/', include('quiz.urls')),  # COMMENTED OUT - Quiz app removed
    path('tasks/', include('tasks.urls')),
    path('wallet/', include('wallet.urls')),
    path('payments/', include('payments.urls')),
    path('subscriptions/', include('subscriptions.urls')),
    path('zoom/', include('zoom_integration.urls')),
    path('notifications/', include('notifications.urls')),
    path('api/', include('api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)