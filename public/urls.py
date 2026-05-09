from django.urls import path
from . import views

app_name = 'public'

urlpatterns = [
    path('jobs/', views.job_list_public, name='jobs'),
    path('jobs/<int:pk>/', views.job_detail_public, name='job_detail'),
]