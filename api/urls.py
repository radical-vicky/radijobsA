from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('', views.api_root, name='root'),
    path('jobs/', views.jobs_list, name='jobs'),
    path('wallet/', views.my_wallet, name='wallet'),
    path('transactions/', views.my_transactions, name='transactions'),
]