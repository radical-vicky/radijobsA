from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:pk>/', views.notification_detail, name='detail'),
    path('<int:pk>/read/', views.mark_read, name='mark_read'),
    path('<int:pk>/unread/', views.mark_unread, name='mark_unread'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('preferences/', views.notification_preferences, name='preferences'),
    
    # API endpoints for AJAX
    path('api/list/', views.api_notification_list, name='api_list'),
    path('api/count/', views.api_notification_count, name='api_count'),
    path('api/<int:pk>/read/', views.api_mark_read, name='api_mark_read'),
    path('api/<int:pk>/archive/', views.api_archive_notification, name='api_archive'),
    path('api/<int:pk>/unarchive/', views.api_unarchive_notification, name='api_unarchive'),
    path('api/archive-all/', views.api_archive_all, name='api_archive_all'),
    path('api/<int:pk>/delete/', views.api_delete_notification, name='api_delete'),
    path('api/mark-all-read/', views.api_mark_all_read, name='api_mark_all_read'),
]