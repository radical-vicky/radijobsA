from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .services import zoom_service
from application.models import Application


@login_required
@user_passes_test(lambda u: u.is_admin)
def schedule_interview(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    
    if request.method == 'POST':
        start_datetime_str = request.POST.get('start_datetime')
        start_datetime = datetime.fromisoformat(start_datetime_str)
        
        # Make timezone aware
        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
        
        try:
            meeting = zoom_service.create_meeting(
                topic=f"Interview: {application.job.title} - {application.user.username}",
                start_time=start_datetime,
                duration_minutes=60
            )
            
            application.interview_date = start_datetime
            application.interview_zoom_link = meeting['join_url']
            application.status = 'interview_scheduled'
            application.save()
            
            messages.success(request, f"Interview scheduled! Zoom link: {meeting['join_url']}")
            return redirect('application:admin_applications')
            
        except Exception as e:
            messages.error(request, f"Failed to create Zoom meeting: {str(e)}")
    
    return render(request, 'zoom/schedule_interview.html', {'application': application})


@login_required
@user_passes_test(lambda u: u.is_admin)
def schedule_onboarding(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    
    if request.method == 'POST':
        start_datetime_str = request.POST.get('start_datetime')
        start_datetime = datetime.fromisoformat(start_datetime_str)
        
        # Make timezone aware
        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
        
        try:
            meeting = zoom_service.create_meeting(
                topic=f"Onboarding: {application.job.title} - {application.user.username}",
                start_time=start_datetime,
                duration_minutes=45
            )
            
            application.onboarding_date = start_datetime
            application.onboarding_zoom_link = meeting['join_url']
            application.save()
            
            messages.success(request, f"Onboarding scheduled! Zoom link: {meeting['join_url']}")
            return redirect('application:admin_applications')
            
        except Exception as e:
            messages.error(request, f"Failed to create Zoom meeting: {str(e)}")
    
    return render(request, 'zoom/schedule_onboarding.html', {'application': application})


@login_required
def my_meetings(request):
    """View all meetings for the logged-in user"""
    # Get applications with scheduled interviews OR onboarding
    applications = Application.objects.filter(user=request.user)
    
    meetings = []
    for app in applications:
        # Check for interview meetings
        if app.interview_zoom_link and app.interview_date:
            meetings.append({
                'title': f"Interview: {app.job.title}",
                'start_time': app.interview_date,
                'duration': 60,
                'join_url': app.interview_zoom_link,
                'type': 'Interview'
            })
        
        # Check for onboarding meetings
        if app.onboarding_zoom_link and app.onboarding_date:
            meetings.append({
                'title': f"Onboarding: {app.job.title}",
                'start_time': app.onboarding_date,
                'duration': 45,
                'join_url': app.onboarding_zoom_link,
                'type': 'Onboarding'
            })
    
    # Sort meetings by start time (upcoming first)
    meetings.sort(key=lambda x: x['start_time'] if x['start_time'] else datetime.max)
    
    context = {
        'meetings': meetings,
    }
    return render(request, 'zoom/my_meetings.html', context)