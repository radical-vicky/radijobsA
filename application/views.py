from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
from .models import Application
from .forms import ApplicationForm
from jobs.models import Job
from notifications.models import create_notification
from zoom_integration.services import create_meeting


@login_required
def apply_for_job(request, job_id):
    """Apply for a job with project submission"""
    job = get_object_or_404(Job, pk=job_id, is_active=True)
    
    if not request.user.has_active_subscription:
        messages.error(request, "You need an active subscription to apply for jobs.")
        return redirect('subscriptions:subscribe')
    
    if Application.objects.filter(user=request.user, job=job).exists():
        messages.warning(request, "You have already applied for this job.")
        return redirect('jobs:dashboard_job_detail', pk=job_id)
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.job = job
            application.status = 'pending'
            application.save()
            
            # Notify admin
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                create_notification(
                    user=admin,
                    notification_type='application',
                    title='New Application Received',
                    message=f'{request.user.get_full_name() or request.user.username} applied for {job.title} with project submission',
                    link=f'/applications/admin/{application.id}/'
                )
            
            # Send confirmation to applicant
            create_notification(
                user=request.user,
                notification_type='application',
                title='Application Submitted Successfully',
                message=f'Your application for {job.title} has been submitted. We will review your project and get back to you soon.',
                link=f'/applications/my/'
            )
            
            messages.success(request, "Application submitted successfully! We will review your project and contact you soon.")
            return redirect('application:my_applications')
    else:
        form = ApplicationForm()
    
    return render(request, 'applications/apply.html', {
        'form': form,
        'job': job,
        'requires_project': True
    })


@login_required
def my_applications(request):
    """View user's applications"""
    applications = Application.objects.filter(user=request.user).select_related('job').order_by('-created_at')
    
    # Calculate statistics
    total_applications = applications.count()
    pending_applications = applications.filter(status='pending').count()
    shortlisted_applications = applications.filter(status='shortlisted').count()
    hired_applications = applications.filter(status='hired').count()
    
    context = {
        'applications': applications,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'shortlisted_applications': shortlisted_applications,
        'hired_applications': hired_applications,
    }
    return render(request, 'applications/my_applications.html', context)


@login_required
def application_detail(request, pk):
    """View single application details"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    return render(request, 'applications/application_detail.html', {'application': application})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_applications(request):
    """Admin view all applications"""
    applications = Application.objects.all().select_related('user', 'job').order_by('-created_at')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    search_query = request.GET.get('search', '')
    if search_query:
        applications = applications.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(job__title__icontains=search_query)
        )
    
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    stats = {
        'total': Application.objects.count(),
        'pending': Application.objects.filter(status='pending').count(),
        'shortlisted': Application.objects.filter(status='shortlisted').count(),
        'approved': Application.objects.filter(status='approved').count(),
        'interview_scheduled': Application.objects.filter(status='interview_scheduled').count(),
        'hired': Application.objects.filter(status='hired').count(),
        'rejected': Application.objects.filter(status='rejected').count(),
    }
    
    context = {
        'applications': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'admin/applications.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_application_detail(request, pk):
    """Admin view single application details"""
    application = get_object_or_404(Application, pk=pk)
    return render(request, 'admin/application_detail.html', {'application': application})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_shortlist_application(request, pk):
    """Admin shortlist application after project review"""
    application = get_object_or_404(Application, pk=pk)
    
    if application.status == 'pending':
        application.shortlist(request.user)
        messages.success(request, f'Application for {application.job.title} has been shortlisted.')
    else:
        messages.warning(request, f'Application status is already {application.get_status_display()}')
    
    return redirect('application:admin_applications')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_approve_application(request, pk):
    """Admin approve application for interview"""
    application = get_object_or_404(Application, pk=pk)
    
    if application.status == 'shortlisted':
        application.approve_for_interview(request.user)
        messages.success(request, f'Application for {application.job.title} has been approved for interview.')
    else:
        messages.warning(request, f'Application must be shortlisted first.')
    
    return redirect('application:admin_applications')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_reject_application(request, pk):
    """Admin reject application with feedback"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
        feedback = request.POST.get('feedback', '')
        application.reject(request.user, feedback)
        messages.success(request, f'Application for {application.job.title} has been rejected.')
        return redirect('application:admin_applications')
    
    return render(request, 'admin/reject_application.html', {'application': application})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_schedule_interview(request, pk):
    """Admin schedule Zoom interview - Only real Zoom meetings"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
        interview_date_str = request.POST.get('interview_date')
        interview_time_str = request.POST.get('interview_time')
        
        # Combine date and time
        interview_datetime = datetime.strptime(f"{interview_date_str} {interview_time_str}", "%Y-%m-%d %H:%M")
        
        # Make timezone aware
        if timezone.is_naive(interview_datetime):
            interview_datetime = timezone.make_aware(interview_datetime)
        
        # Create real Zoom meeting
        meeting = create_meeting(
            topic=f"Interview: {application.job.title} - {application.user.username}",
            start_time=interview_datetime,
            duration_minutes=60
        )
        
        if meeting.get('success'):
            # Schedule interview with real Zoom link (this creates ZoomMeeting record internally)
            application.schedule_interview(interview_datetime, meeting['join_url'])
            
            messages.success(request, f'✓ Interview scheduled successfully!')
            messages.success(request, f'✓ Zoom meeting created: {meeting["join_url"]}')
            messages.success(request, f'✓ Notification and email sent to {application.user.email}')
        else:
            error_message = meeting.get('error', 'Unknown error')
            messages.error(request, f'✗ Failed to create Zoom meeting: {error_message}')
            messages.error(request, 'Please check your Zoom API credentials and try again.')
            return redirect('application:admin_applications')
        
        return redirect('application:admin_applications')
    
    return render(request, 'admin/schedule_interview.html', {'application': application})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_complete_interview(request, pk):
    """Mark interview as completed"""
    application = get_object_or_404(Application, pk=pk)
    application.complete_interview()
    messages.success(request, f'Interview marked as completed for {application.user.username}.')
    return redirect('application:admin_applications')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_hire_application(request, pk):
    """Admin hire applicant"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        if not start_date:
            messages.error(request, "Please select a start date.")
            return render(request, 'admin/hire_application.html', {'application': application})
        
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        application.hire(start_date_obj)
        messages.success(request, f'{application.user.get_full_name()} has been hired for {application.job.title}! Start date: {start_date_obj.strftime("%B %d, %Y")}')
        
        return redirect('application:admin_applications')
    
    return render(request, 'admin/hire_application.html', {'application': application})