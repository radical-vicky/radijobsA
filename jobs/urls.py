from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Public URLs
    path('', views.job_list, name='list'),
    path('<int:pk>/', views.job_detail, name='detail'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    
    # Save/Unsave URLs
    path('save/<int:job_id>/', views.save_job, name='save_job'),
    path('saved/', views.saved_jobs, name='saved_jobs'),
    path('unsave/<int:job_id>/', views.unsave_job, name='unsave_job'),
    
    # Dashboard URLs
    path('dashboard/', views.dashboard_job_list, name='dashboard_jobs'),
    path('dashboard/<int:pk>/', views.dashboard_job_detail, name='dashboard_job_detail'),
]