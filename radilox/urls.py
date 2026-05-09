"""
URL configuration for radilox project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Allauth URLs (authentication)
    path('accounts/', include('allauth.urls')),
    
    # Home and public pages
    path('', include('home.urls')),
    path('public/', include('public.urls')),
    
    # Dashboard
    path('dashboard/', include('accounts.urls')),
    
    # Jobs
    path('jobs/', include('jobs.urls')),
    
    # Applications (note: 'application' not 'applications')
    path('applications/', include('application.urls')),
    
    # Quiz
    path('quiz/', include('quiz.urls')),
    
    # Tasks
    path('tasks/', include('tasks.urls')),
    
    # Wallet
    path('wallet/', include('wallet.urls')),
    
    # Payments & Subscriptions
    path('payments/', include('payments.urls')),
    path('subscriptions/', include('subscriptions.urls')),
    
    # Zoom Integration
    path('zoom/', include('zoom_integration.urls')),
    
    # Notifications
    path('notifications/', include('notifications.urls')),
    
    # API endpoints
    path('api/', include('api.urls')),
    
    # HTMX is just a library, no URLs needed
    # path("htmx/", include("django_htmx.urls")),  # REMOVE THIS LINE - it doesn't exist
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = 'home.views.custom_404'
handler500 = 'home.views.custom_500'