from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('subscribe/', views.subscribe, name='subscribe'),
    path('status/', views.subscription_status, name='status'),
    path('cancel/', views.cancel_subscription, name='cancel'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('mpesa-callback/', views.mpesa_callback, name='mpesa_callback'),  # Add this line
]