from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Application
from .forms import ApplicationForm
from jobs.models import Job
from notifications.models import create_notification


@login_required
def apply_for_job(request, job_id):
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
            
            # Create notification for admin
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(role='admin')
            for admin in admins:
                create_notification(
                    user=admin,
                    notification_type='application',
                    title='New Application Received',
                    message=f'{request.user.get_full_name() or request.user.username} applied for {job.title}',
                    link='/applications/admin/'
                )
            
            messages.success(request, "Application submitted successfully! Wait for admin approval.")
            return redirect('application:my_applications')
    else:
        form = ApplicationForm()
    
    return render(request, 'applications/apply.html', {'form': form, 'job': job})


@login_required
def my_applications(request):
    applications = Application.objects.filter(user=request.user).select_related('job').order_by('-created_at')
    return render(request, 'applications/my_applications.html', {'applications': applications})


@login_required
@user_passes_test(lambda u: u.is_admin)
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
        'approved': Application.objects.filter(status='approved').count(),
        'interview': Application.objects.filter(status='interview_scheduled').count(),
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
@user_passes_test(lambda u: u.is_admin)
def admin_application_detail(request, pk):
    """Admin view single application details"""
    application = get_object_or_404(Application, pk=pk)
    return render(request, 'admin/application_detail.html', {'application': application})


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_approve_application(request, pk):
    """Admin approve application and schedule quiz"""
    application = get_object_or_404(Application, pk=pk)
    
    if application.status == 'pending':
        application.status = 'approved'
        
        # Set quiz deadline (7 days from approval)
        application.quiz_expires_at = timezone.now() + timedelta(days=7)
        application.quiz_duration_minutes = 30
        application.save()
        
        # Create notification for applicant
        create_notification(
            user=application.user,
            notification_type='quiz',
            title='Technical Quiz Available',
            message=f'Your application for {application.job.title} has been approved! Complete the technical quiz by {application.quiz_expires_at.strftime("%B %d, %Y at %H:%M")}. You have 30 minutes to complete it.',
            link=f'/quiz/take/{application.id}/'
        )
        
        messages.success(request, f'Application for {application.job.title} has been approved. Quiz notification sent to applicant.')
    else:
        messages.warning(request, f'Application status is already {application.get_status_display()}')
    
    return redirect('application:admin_applications')


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_reject_application(request, pk):
    """Admin reject application"""
    application = get_object_or_404(Application, pk=pk)
    
    if application.status == 'pending':
        application.status = 'rejected'
        application.save()
        
        create_notification(
            user=application.user,
            notification_type='application',
            title='Application Update',
            message=f'Thank you for applying to {application.job.title}. After careful review, your application was not selected.',
            link='/applications/my/'
        )
        
        messages.success(request, f'Application for {application.job.title} has been rejected.')
    else:
        messages.warning(request, f'Application status is already {application.get_status_display()}')
    
    return redirect('application:admin_applications')


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_schedule_interview(request, pk):
    """Admin schedule interview for applicant"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
        interview_date = request.POST.get('interview_date')
        interview_link = request.POST.get('interview_link')
        
        application.status = 'interview_scheduled'
        application.interview_date = interview_date
        application.interview_zoom_link = interview_link
        application.save()
        
        create_notification(
            user=application.user,
            notification_type='interview',
            title='Interview Scheduled',
            message=f'Your interview for {application.job.title} has been scheduled.',
            link=interview_link or '/zoom/my/'
        )
        
        messages.success(request, f'Interview scheduled for {application.user.get_full_name() or application.user.username}')
        return redirect('application:admin_applications')
    
    return render(request, 'admin/schedule_interview.html', {'application': application})