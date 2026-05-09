from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('freelancer/', views.freelancer_dashboard, name='freelancer_dashboard'),
    path('applicant/', views.applicant_dashboard, name='applicant_dashboard'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Payment Methods
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    path('payment-methods/<int:pk>/set-default/', views.set_default_payment_method, name='set_default_payment_method'),
    path('payment-methods/<int:pk>/delete/', views.delete_payment_method, name='delete_payment_method'),
    
    # Admin User Management
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    path('users/<int:pk>/change-role/', views.user_change_role, name='user_change_role'),
    path('users/export/', views.user_export, name='user_export'),
    
    # AJAX Endpoints
    path('api/notifications/count/', views.get_notifications_ajax, name='get_notifications_ajax'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]