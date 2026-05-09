from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Public URLs (no sidebar - for unauthenticated users)
    path('', views.job_list, name='list'),
    path('<int:pk>/', views.job_detail, name='detail'),
    
    # Dashboard URLs (with sidebar - for authenticated users)
    path('dashboard/', views.dashboard_job_list, name='dashboard_jobs'),
    path('dashboard/<int:pk>/', views.dashboard_job_detail, name='dashboard_job_detail'),
    
    # Admin URLs
    path('admin/dashboard/', views.admin_job_dashboard, name='admin_dashboard'),
    path('admin/create/', views.job_create, name='create'),
    path('admin/<int:pk>/edit/', views.job_edit, name='edit'),
    path('admin/<int:pk>/delete/', views.job_delete, name='delete'),
    path('admin/<int:pk>/toggle/', views.job_toggle_status, name='toggle'),
    path('admin/<int:pk>/duplicate/', views.job_duplicate, name='duplicate'),
    path('admin/bulk-action/', views.job_bulk_action, name='bulk_action'),
    path('admin/export/', views.job_export, name='export'),
    path('admin/<int:pk>/applications/', views.job_applications_view, name='applications'),
    
    # AJAX endpoints
    path('quick-view/<int:pk>/', views.job_quick_view, name='quick_view'),
    path('search-suggestions/', views.job_search_suggestions, name='search_suggestions'),
    path('filter-options/', views.job_filter_options, name='filter_options'),
]