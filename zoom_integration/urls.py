from django.urls import path
from . import views

app_name = 'zoom'

urlpatterns = [
    path('my/', views.my_meetings, name='my_meetings'),
    path('schedule-interview/<int:application_id>/', views.schedule_interview, name='schedule_interview'),
    path('schedule-onboarding/<int:application_id>/', views.schedule_onboarding, name='schedule_onboarding'),
]