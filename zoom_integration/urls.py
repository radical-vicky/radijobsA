from django.urls import path
from . import views

app_name = 'zoom_integration'

urlpatterns = [
    # Put named routes BEFORE the dynamic route
    path('my/', views.my_meetings, name='my_meetings'),
    path('schedule-interview/<int:application_id>/', views.schedule_interview, name='schedule_interview'),
    path('create/', views.create_meeting_view, name='create_meeting'),
    # This dynamic route should be LAST
    path('<str:meeting_id>/', views.meeting_detail, name='meeting_detail'),
]