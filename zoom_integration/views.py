from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .services import create_meeting
from .models import ZoomMeeting


@login_required
def my_meetings(request):
    """View all Zoom meetings for the logged-in user with proper status handling"""
    all_meetings = ZoomMeeting.objects.filter(user=request.user).order_by('start_time')
    
    upcoming_meetings = []
    ongoing_meetings = []
    postponed_meetings = []
    past_meetings = []
    
    for meeting in all_meetings:
        # Skip cancelled meetings entirely
        if meeting.status == 'cancelled':
            continue
            
        job_title = meeting.application.job.title if meeting.application and meeting.application.job else "Interview"
        
        meeting_data = {
            'id': meeting.id,
            'title': meeting.topic,
            'job_title': job_title,
            'type': meeting.meeting_type,
            'start_time': meeting.start_time,
            'duration': meeting.duration_minutes,
            'join_url': meeting.join_url,
            'image_url': meeting.application.job.get_image_url if meeting.application and meeting.application.job else None,
            'status': meeting.status,
        }
        
        now = timezone.now()
        
        if meeting.status == 'ongoing':
            ongoing_meetings.append(meeting_data)
        elif meeting.status == 'postponed':
            postponed_meetings.append(meeting_data)
        elif meeting.status == 'scheduled' and meeting.start_time > now:
            upcoming_meetings.append(meeting_data)
        elif meeting.status == 'completed':
            past_meetings.append(meeting_data)
        elif meeting.status == 'scheduled' and meeting.start_time <= now:
            past_meetings.append(meeting_data)
    
    context = {
        'upcoming_meetings': upcoming_meetings,
        'ongoing_meetings': ongoing_meetings,
        'postponed_meetings': postponed_meetings,
        'past_meetings': past_meetings,
        'upcoming_count': len(upcoming_meetings),
        'ongoing_count': len(ongoing_meetings),
        'postponed_count': len(postponed_meetings),
        'past_count': len(past_meetings),
        'total_count': all_meetings.exclude(status='cancelled').count(),
    }
    return render(request, 'zoom/my_meetings.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_meeting_status(request, meeting_id, status):
    """Update meeting status (ongoing/completed/cancelled/postponed)"""
    meeting = get_object_or_404(ZoomMeeting, id=meeting_id)
    
    if status == 'ongoing':
        meeting.mark_ongoing()
        messages.success(request, f'Meeting "{meeting.topic}" is now ongoing.')
    elif status == 'completed':
        meeting.mark_completed()
        messages.success(request, f'Meeting "{meeting.topic}" has been marked as completed.')
    elif status == 'cancelled':
        meeting.cancel()
        messages.success(request, f'Meeting "{meeting.topic}" has been cancelled.')
    elif status == 'postponed':
        meeting.postpone()
        messages.success(request, f'Meeting "{meeting.topic}" has been postponed.')
    else:
        messages.error(request, 'Invalid status update.')
    
    return redirect('admin:zoom_integration_zoommeeting_changelist')


@staff_member_required
def schedule_interview(request, application_id):
    """Schedule an interview for an application"""
    from application.models import Application
    
    application = get_object_or_404(Application, pk=application_id)
    
    if request.method == 'POST':
        interview_date = request.POST.get('interview_date')
        interview_time = request.POST.get('interview_time')
        duration = int(request.POST.get('duration', 60))
        
        interview_datetime = datetime.strptime(f"{interview_date} {interview_time}", "%Y-%m-%d %H:%M")
        
        if timezone.is_naive(interview_datetime):
            interview_datetime = timezone.make_aware(interview_datetime)
        
        meeting = create_meeting(
            topic=f"Interview: {application.job.title} - {application.user.username}",
            start_time=interview_datetime,
            duration_minutes=duration
        )
        
        if meeting.get('success'):
            zoom_meeting = ZoomMeeting.objects.create(
                user=application.user,
                application=application,
                meeting_id=meeting['meeting_id'],
                topic=meeting.get('topic', f"Interview: {application.job.title}"),
                meeting_type='interview',
                start_time=interview_datetime,
                duration_minutes=duration,
                join_url=meeting['join_url'],
                status='scheduled'
            )
            
            application.interview_scheduled_at = interview_datetime
            application.interview_link = meeting['join_url']
            application.status = 'interview_scheduled'
            application.save()
            
            messages.success(request, f'✓ Interview scheduled! Meeting link: {meeting["join_url"]}')
        else:
            messages.error(request, f'Failed to create meeting: {meeting.get("error")}')
        
        return redirect('application:admin_applications')
    
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
        
        if meeting.get('success'):
            zoom_meeting = ZoomMeeting.objects.create(
                meeting_id=meeting['meeting_id'],
                topic=topic,
                start_time=start_datetime,
                duration_minutes=duration,
                join_url=meeting['join_url'],
                status='scheduled'
            )
            messages.success(request, f'Zoom meeting created: {zoom_meeting.join_url}')
            return redirect('admin:zoom_integration_zoommeeting_changelist')
        else:
            messages.error(request, f'Failed to create meeting: {meeting.get("error")}')
    
    return render(request, 'zoom/create_meeting.html')


@login_required
def meeting_detail(request, meeting_id):
    """View meeting details"""
    meeting = get_object_or_404(ZoomMeeting, meeting_id=meeting_id)
    
    if meeting.application and meeting.application.user != request.user:
        if not request.user.is_superuser:
            messages.error(request, "You don't have permission to view this meeting.")
            return redirect('zoom_integration:my_meetings')
    
    return render(request, 'zoom/meeting_detail.html', {'meeting': meeting})



@login_required
@user_passes_test(lambda u: u.is_superuser)
def reschedule_meeting(request):
    """Reschedule a postponed meeting"""
    if request.method == 'POST':
        meeting_id = request.POST.get('meeting_id')
        new_date = request.POST.get('new_date')
        new_time = request.POST.get('new_time')
        postpone_reason = request.POST.get('postpone_reason')
        
        meeting = get_object_or_404(ZoomMeeting, id=meeting_id)
        
        new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
        if timezone.is_naive(new_datetime):
            new_datetime = timezone.make_aware(new_datetime)
        
        # Create new Zoom meeting
        new_meeting = create_meeting(
            topic=meeting.topic,
            start_time=new_datetime,
            duration_minutes=meeting.duration_minutes
        )
        
        if new_meeting.get('success'):
            meeting.reschedule(new_datetime, new_meeting['join_url'])
            meeting.postpone_reason = postpone_reason
            meeting.save()
            messages.success(request, f'Meeting rescheduled to {new_datetime.strftime("%B %d, %Y at %H:%M")}')
        else:
            messages.error(request, f'Failed to reschedule: {new_meeting.get("error")}')
        
        return redirect('zoom_integration:my_meetings')
    
    return redirect('zoom_integration:my_meetings')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def cancel_meeting(request, meeting_id):
    """Cancel a meeting"""
    meeting = get_object_or_404(ZoomMeeting, id=meeting_id)
    meeting.cancel()
    messages.success(request, f'Meeting "{meeting.topic}" has been cancelled.')
    return redirect('zoom_integration:my_meetings')