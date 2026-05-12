from django.urls import path
from . import views

app_name = 'zoom_integration'

urlpatterns = [
    path('my/', views.my_meetings, name='my_meetings'),
    path('schedule/<int:application_id>/', views.schedule_interview, name='schedule_interview'),
    path('create/', views.create_meeting_view, name='create_meeting'),
    path('detail/<str:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    path('update-status/<int:meeting_id>/<str:status>/', views.update_meeting_status, name='update_status'),
    path('reschedule/', views.reschedule_meeting, name='reschedule_meeting'),
    path('reschedule/', views.reschedule_meeting, name='reschedule'),
    path('cancel/<int:meeting_id>/', views.cancel_meeting, name='cancel_meeting'),
]