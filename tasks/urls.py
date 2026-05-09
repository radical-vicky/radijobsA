from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # Freelancer URLs
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('<int:pk>/', views.task_detail, name='detail'),
    path('<int:pk>/start/', views.start_task, name='start'),
    path('<int:pk>/submit/', views.submit_task, name='submit'),
    
    # Admin URLs
    path('admin/', views.admin_tasks, name='admin_tasks'),
    path('admin/assign/', views.assign_task, name='assign'),
    path('admin/review/<int:pk>/', views.review_task, name='review'),
    path('admin/pay/<int:pk>/', views.pay_task, name='pay'),
    path('admin/analytics/', views.task_analytics, name='analytics'),
]