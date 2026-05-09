from django.urls import path
from . import views

app_name = 'application'

urlpatterns = [
    # Applicant URLs
    path('apply/<int:job_id>/', views.apply_for_job, name='apply'),
    path('my/', views.my_applications, name='my_applications'),
    
    # Admin URLs
    path('admin/', views.admin_applications, name='admin_applications'),
    path('admin/<int:pk>/', views.admin_application_detail, name='admin_application_detail'),
    path('admin/<int:pk>/approve/', views.admin_approve_application, name='admin_approve'),
    path('admin/<int:pk>/reject/', views.admin_reject_application, name='admin_reject'),
    path('admin/<int:pk>/schedule/', views.admin_schedule_interview, name='admin_schedule_interview'),
]