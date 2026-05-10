from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .services import create_meeting
from .models import ZoomMeeting


@login_required
def my_meetings(request):
    """View user's Zoom meetings"""
    meetings = ZoomMeeting.objects.filter(
        application__user=request.user
    ).order_by('-start_time')
    return render(request, 'zoom/my_meetings.html', {'meetings': meetings})


@staff_member_required
def schedule_interview(request, application_id):
    """Schedule an interview for an application"""
    from application.models import Application
    
    application = get_object_or_404(Application, pk=application_id)
    
    if request.method == 'POST':
        interview_date = request.POST.get('interview_date')
        interview_time = request.POST.get('interview_time')
        duration = int(request.POST.get('duration', 60))
        
        # Combine date and time
        interview_datetime = datetime.strptime(f"{interview_date} {interview_time}", "%Y-%m-%d %H:%M")
        
        # Make timezone aware
        if timezone.is_naive(interview_datetime):
            interview_datetime = timezone.make_aware(interview_datetime)
        
        # Create Zoom meeting
        meeting = create_meeting(
            topic=f"Interview: {application.job.title} - {application.user.username}",
            start_time=interview_datetime,
            duration_minutes=duration
        )
        
        if meeting['success']:
            # Create Zoom meeting record
            zoom_meeting = ZoomMeeting.objects.create(
                meeting_id=meeting['meeting_id'],
                topic=meeting.get('topic', f"Interview: {application.job.title}"),
                start_time=interview_datetime,
                duration_minutes=duration,
                join_url=meeting['join_url'],
                start_url=meeting['start_url'],
                application=application
            )
            
            # Update application with interview details
            application.interview_scheduled_at = interview_datetime
            application.interview_link = meeting['join_url']
            application.status = 'interview_scheduled'
            application.save()
            
            messages.success(request, f'Interview scheduled! Meeting link: {meeting["join_url"]}')
            return redirect('application:admin_applications')
        else:
            messages.error(request, f'Failed to create meeting: {meeting.get("error")}')
    
    return render(request, 'zoom/schedule_interview.html', {'application': application})


@staff_member_required
def create_meeting_view(request):
    """Create a Zoom meeting"""
    if request.method == 'POST':
        topic = request.POST.get('topic')
        start_date = request.POST.get('start_date')
        start_time = request.POST.get('start_time')
        duration = int(request.POST.get('duration', 60))
        
        start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
        
        meeting = create_meeting(topic, start_datetime, duration)
        
        if meeting['success']:
            zoom_meeting = ZoomMeeting.objects.create(
                meeting_id=meeting['meeting_id'],
                topic=topic,
                start_time=start_datetime,
                duration_minutes=duration,
                join_url=meeting['join_url'],
                start_url=meeting['start_url']
            )
            messages.success(request, f'Zoom meeting created: {zoom_meeting.join_url}')
            return redirect('admin:zoom_integration_zoommeeting_changelist')
        else:
            messages.error(request, f'Failed to create meeting: {meeting.get("error")}')
    
    return render(request, 'zoom/create_meeting.html')


@login_required
def meeting_detail(request, meeting_id):
    """View meeting details"""
    # First try to get by meeting_id string
    meeting = get_object_or_404(ZoomMeeting, meeting_id=meeting_id)
    
    # Check if user has access to this meeting
    if meeting.application and meeting.application.user != request.user:
        if not request.user.is_admin and not request.user.is_staff:
            messages.error(request, "You don't have permission to view this meeting.")
            return redirect('zoom_integration:my_meetings')
    
    return render(request, 'zoom/meeting_detail.html', {'meeting': meeting})