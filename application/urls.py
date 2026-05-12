from django.urls import path
from . import views

app_name = 'application'

urlpatterns = [
    # User URLs
    path('apply/<int:job_id>/', views.apply_for_job, name='apply'),
    path('my/', views.my_applications, name='my_applications'),
    path('detail/<int:pk>/', views.application_detail, name='detail'),
    
    # Admin URLs
    path('admin/', views.admin_applications, name='admin_applications'),
    path('admin/<int:pk>/', views.admin_application_detail, name='admin_detail'),
    path('admin/<int:pk>/shortlist/', views.admin_shortlist_application, name='admin_shortlist'),
    path('admin/<int:pk>/approve/', views.admin_approve_application, name='admin_approve'),
    path('admin/<int:pk>/reject/', views.admin_reject_application, name='admin_reject'),
    path('admin/<int:pk>/schedule-interview/', views.admin_schedule_interview, name='admin_schedule_interview'),
    path('admin/<int:pk>/complete-interview/', views.admin_complete_interview, name='admin_complete_interview'),
    path('admin/<int:pk>/hire/', views.admin_hire_application, name='admin_hire'),
]