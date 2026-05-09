from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.core.cache import cache
from .models import Job
from .forms import JobForm
from application.models import Application
from notifications.models import create_notification

# ==================== PUBLIC VIEWS ====================

@vary_on_headers('Cookie')
def job_list(request):
    """Public job listings page with caching and filtering"""
    
    # Get base queryset
    jobs = Job.objects.filter(is_active=True)
    
    # Search and filter parameters
    search_query = request.GET.get('q', '').strip()
    job_type = request.GET.get('type', '')
    experience = request.GET.get('experience', '')
    location = request.GET.get('location', '')
    min_salary = request.GET.get('min_salary', '')
    max_salary = request.GET.get('max_salary', '')
    skills = request.GET.get('skills', '')
    
    # Apply filters
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(requirements__icontains=search_query)
        )
    
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    if experience:
        jobs = jobs.filter(experience_level=experience)
    
    if location:
        jobs = jobs.filter(location__icontains=location)
    
    if min_salary:
        # Extract numeric values from salary range
        jobs = jobs.filter(salary_range__icontains=min_salary)
    
    if skills:
        skills_list = [s.strip() for s in skills.split(',')]
        for skill in skills_list:
            jobs = jobs.filter(skills_required__icontains=skill)
    
    # Order by newest first
    jobs = jobs.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(jobs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get unique locations and skills for filter dropdowns
    unique_locations = Job.objects.filter(is_active=True).values_list('location', flat=True).distinct()[:10]
    common_skills = ['Python', 'Django', 'React', 'JavaScript', 'Java', 'AWS', 'Docker', 'Kubernetes']
    
    context = {
        'jobs': page_obj,
        'search_query': search_query,
        'selected_type': job_type,
        'selected_experience': experience,
        'selected_location': location,
        'min_salary': min_salary,
        'max_salary': max_salary,
        'skills': skills,
        'unique_locations': unique_locations,
        'common_skills': common_skills,
        'total_jobs': jobs.count(),
    }
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, pk):
    """Public job detail page with related jobs"""
    
    # Get the main job
    job = get_object_or_404(Job, pk=pk, is_active=True)
    
    # Increment view count (if you add a view_count field)
    # job.view_count += 1
    # job.save()
    
    # Check if user has already applied
    has_applied = False
    application_status = None
    if request.user.is_authenticated:
        application = Application.objects.filter(user=request.user, job=job).first()
        if application:
            has_applied = True
            application_status = application.status
    
    # Get related jobs (same job type or similar skills)
    related_jobs = Job.objects.filter(
        Q(job_type=job.job_type) | 
        Q(skills_required__overlap=job.skills_required),
        is_active=True
    ).exclude(id=job.id)[:3]
    
    # Get similar jobs by skills
    similar_jobs = []
    if job.skills_required:
        similar_jobs = Job.objects.filter(
            skills_required__overlap=job.skills_required,
            is_active=True
        ).exclude(id=job.id)[:3]
    
    context = {
        'job': job,
        'has_applied': has_applied,
        'application_status': application_status,
        'related_jobs': related_jobs,
        'similar_jobs': similar_jobs,
    }
    return render(request, 'jobs/job_detail.html', context)

def job_share(request, pk):
    """Share job via email or social media (AJAX)"""
    if request.method == 'POST':
        job = get_object_or_404(Job, pk=pk, is_active=True)
        email = request.POST.get('email')
        
        if email:
            # Send email sharing logic here
            # send_shared_job_email(job, email, request.user)
            messages.success(request, f"Job shared successfully to {email}")
        else:
            messages.error(request, "Please provide an email address")
        
        return redirect('jobs:detail', pk=job.id)
    
    return redirect('jobs:detail', pk=pk)

def job_save(request, pk):
    """Save job to user's saved jobs list"""
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to save jobs")
        return redirect('account_login')
    
    job = get_object_or_404(Job, pk=pk, is_active=True)
    
    # Add to saved jobs (you need a SavedJob model)
    # saved_job, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    
    # if created:
    #     messages.success(request, f"Job '{job.title}' saved successfully")
    # else:
    #     messages.info(request, f"Job '{job.title}' already saved")
    
    return redirect('jobs:detail', pk=job.id)

# ==================== ADMIN VIEWS ====================

@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_job_dashboard(request):
    """Admin dashboard for jobs with statistics"""
    
    # Get all jobs
    all_jobs = Job.objects.all()
    
    # Statistics
    stats = {
        'total_jobs': all_jobs.count(),
        'active_jobs': all_jobs.filter(is_active=True).count(),
        'inactive_jobs': all_jobs.filter(is_active=False).count(),
        'freelance_jobs': all_jobs.filter(job_type='freelance').count(),
        'fulltime_jobs': all_jobs.filter(job_type='fulltime').count(),
        'parttime_jobs': all_jobs.filter(job_type='parttime').count(),
        'jobs_this_month': all_jobs.filter(created_at__month=timezone.now().month).count(),
        'total_applications': Application.objects.filter(job__in=all_jobs).count(),
    }
    
    # Recent jobs
    recent_jobs = all_jobs.order_by('-created_at')[:10]
    
    # Jobs with most applications
    top_jobs = Application.objects.values('job__title', 'job__id').annotate(
        app_count=models.Count('id')
    ).order_by('-app_count')[:5]
    
    context = {
        'stats': stats,
        'recent_jobs': recent_jobs,
        'top_jobs': top_jobs,
    }
    return render(request, 'jobs/admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_create(request):
    """Admin: Create new job"""
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user
            job.save()
            
            # Handle image upload
            if 'image' in request.FILES:
                job.image = request.FILES['image']
                job.save()
            
            messages.success(request, f"Job '{job.title}' created successfully!")
            
            # Send notification to admins (optional)
            # notify_admins_new_job(job)
            
            return redirect('jobs:detail', pk=job.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = JobForm()
    
    return render(request, 'jobs/job_form.html', {
        'form': form,
        'title': 'Create New Job',
        'button_text': 'Create Job'
    })

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_edit(request, pk):
    """Admin: Edit existing job"""
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES, instance=job)
        if form.is_valid():
            job = form.save()
            
            # Handle image update
            if 'image' in request.FILES:
                job.image = request.FILES['image']
                job.save()
            
            messages.success(request, f"Job '{job.title}' updated successfully!")
            return redirect('jobs:detail', pk=job.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = JobForm(instance=job)
    
    return render(request, 'jobs/job_form.html', {
        'form': form,
        'job': job,
        'title': 'Edit Job',
        'button_text': 'Save Changes'
    })

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_delete(request, pk):
    """Admin: Delete job (soft delete or hard delete)"""
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        job_title = job.title
        
        # Check if there are applications
        applications_count = Application.objects.filter(job=job).count()
        
        if applications_count > 0:
            # Soft delete - just mark as inactive
            job.is_active = False
            job.save()
            messages.warning(
                request, 
                f"Job '{job_title}' has been deactivated because it has {applications_count} application(s)."
            )
        else:
            # Hard delete
            job.delete()
            messages.success(request, f"Job '{job_title}' deleted successfully!")
        
        return redirect('jobs:admin_dashboard')
    
    return render(request, 'jobs/job_confirm_delete.html', {'job': job})

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_toggle_status(request, pk):
    """Admin: Toggle job active status"""
    job = get_object_or_404(Job, pk=pk)
    job.is_active = not job.is_active
    job.save()
    
    status = "activated" if job.is_active else "deactivated"
    messages.success(request, f"Job '{job.title}' {status} successfully!")
    
    # Send notification to users who saved this job (optional)
    if job.is_active:
        # notify_users_job_reactivated(job)
        pass
    
    return redirect('jobs:admin_dashboard')

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_bulk_action(request):
    """Admin: Bulk actions on jobs (activate, deactivate, delete)"""
    if request.method == 'POST':
        action = request.POST.get('action')
        job_ids = request.POST.getlist('job_ids')
        
        if not job_ids:
            messages.warning(request, "No jobs selected.")
            return redirect('jobs:admin_dashboard')
        
        jobs = Job.objects.filter(id__in=job_ids)
        
        if action == 'activate':
            count = jobs.update(is_active=True)
            messages.success(request, f"{count} job(s) activated.")
        elif action == 'deactivate':
            count = jobs.update(is_active=False)
            messages.success(request, f"{count} job(s) deactivated.")
        elif action == 'delete':
            count = jobs.count()
            jobs.delete()
            messages.success(request, f"{count} job(s) deleted.")
        else:
            messages.error(request, "Invalid action selected.")
    
    return redirect('jobs:admin_dashboard')

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_export(request):
    """Admin: Export jobs to CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="jobs_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Company', 'Type', 'Location', 'Salary', 'Status', 'Created At', 'Applications'])
    
    jobs = Job.objects.all().prefetch_related('applications')
    
    for job in jobs:
        writer.writerow([
            job.id,
            job.title,
            job.company,
            job.get_job_type_display(),
            job.location,
            job.salary_range,
            'Active' if job.is_active else 'Inactive',
            job.created_at.strftime('%Y-%m-%d'),
            job.applications.count()
        ])
    
    return response

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_duplicate(request, pk):
    """Admin: Duplicate an existing job"""
    original_job = get_object_or_404(Job, pk=pk)
    
    # Create duplicate
    duplicated_job = Job.objects.create(
        title=f"{original_job.title} (Copy)",
        company=original_job.company,
        description=original_job.description,
        requirements=original_job.requirements,
        project_brief=original_job.project_brief,
        salary_range=original_job.salary_range,
        location=original_job.location,
        job_type=original_job.job_type,
        experience_level=original_job.experience_level,
        skills_required=original_job.skills_required,
        image=original_job.image,
        image_url=original_job.image_url,
        created_by=request.user,
        is_active=False  # Set as inactive by default
    )
    
    messages.success(request, f"Job '{original_job.title}' duplicated successfully!")
    return redirect('jobs:edit', pk=duplicated_job.pk)

@login_required
@user_passes_test(lambda u: u.is_admin)
def job_applications_view(request, pk):
    """Admin: View all applications for a specific job"""
    job = get_object_or_404(Job, pk=pk)
    applications = job.applications.all().select_related('user').order_by('-created_at')
    
    # Statistics
    stats = {
        'total': applications.count(),
        'pending': applications.filter(status='pending').count(),
        'approved': applications.filter(status='approved').count(),
        'rejected': applications.filter(status='rejected').count(),
        'hired': applications.filter(status='hired').count(),
    }
    
    context = {
        'job': job,
        'applications': applications,
        'stats': stats,
    }
    return render(request, 'jobs/job_applications.html', context)

# ==================== API-LIKE ENDPOINTS (for AJAX) ====================

@login_required
def job_quick_view(request, pk):
    """AJAX: Quick view modal data"""
    from django.http import JsonResponse
    
    job = get_object_or_404(Job, pk=pk, is_active=True)
    
    data = {
        'id': job.id,
        'title': job.title,
        'company': job.company,
        'description': job.description[:200],
        'salary_range': job.salary_range,
        'location': job.location,
        'job_type': job.get_job_type_display(),
        'experience_level': job.get_experience_level_display(),
        'skills': job.skills_required,
        'image_url': job.get_image_url,
        'url': job.get_absolute_url(),
    }
    
    return JsonResponse(data)

def job_search_suggestions(request):
    """AJAX: Search suggestions for job titles"""
    from django.http import JsonResponse
    
    query = request.GET.get('q', '')
    suggestions = []
    
    if query:
        jobs = Job.objects.filter(
            title__icontains=query,
            is_active=True
        ).values_list('title', flat=True).distinct()[:5]
        
        companies = Job.objects.filter(
            company__icontains=query,
            is_active=True
        ).values_list('company', flat=True).distinct()[:5]
        
        suggestions = list(jobs) + list(companies)
    
    return JsonResponse({'suggestions': suggestions[:10]})

def job_filter_options(request):
    """AJAX: Get filter options for job search"""
    from django.http import JsonResponse
    
    job_types = [{'value': t[0], 'label': t[1]} for t in Job.JOB_TYPE_CHOICES]
    experience_levels = [{'value': e[0], 'label': e[1]} for e in Job.EXPERIENCE_CHOICES]
    locations = Job.objects.filter(is_active=True).values_list('location', flat=True).distinct()
    
    return JsonResponse({
        'job_types': job_types,
        'experience_levels': experience_levels,
        'locations': list(locations),
    })


# Add these imports at the top if not already present
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Add these lines at the very bottom of your jobs/views.py

@login_required
def dashboard_job_list(request):
    """Dashboard job listing page (with sidebar) - for authenticated users"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    jobs = Job.objects.filter(is_active=True)
    
    # Get counts for stats
    freelance_count = jobs.filter(job_type='freelance').count()
    fulltime_count = jobs.filter(job_type='fulltime').count()
    featured_count = jobs.filter(is_featured=True).count()
    
    search_query = request.GET.get('q', '')
    job_type = request.GET.get('type', '')
    experience = request.GET.get('experience', '')
    
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(company__icontains=search_query)
        )
    
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    if experience:
        jobs = jobs.filter(experience_level=experience)
    
    jobs = jobs.order_by('-created_at')
    
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'jobs': page_obj,
        'total_jobs': jobs.count(),
        'freelance_count': freelance_count,
        'fulltime_count': fulltime_count,
        'featured_count': featured_count,
        'search_query': search_query,
        'selected_type': job_type,
        'selected_experience': experience,
    }
    return render(request, 'dashboard/jobs_list.html', context)


@login_required
def dashboard_job_detail(request, pk):
    """Dashboard job detail page (with sidebar) - for authenticated users"""
    from application.models import Application
    
    job = get_object_or_404(Job, pk=pk, is_active=True)
    
    # Increment view count
    job.view_count = (job.view_count or 0) + 1
    job.save()
    
    # Check if user has already applied
    has_applied = False
    application_status = None
    if request.user.is_authenticated:
        application = Application.objects.filter(user=request.user, job=job).first()
        if application:
            has_applied = True
            application_status = application.status
    
    context = {
        'job': job,
        'has_applied': has_applied,
        'application_status': application_status,
    }
    return render(request, 'dashboard/job_detail.html', context)