from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from .models import Job, JobCategory, SavedJob


def job_list(request):
    """Public job listing page"""
    jobs = Job.objects.filter(is_active=True, expires_at__gt=timezone.now())
    
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(skills_required__icontains=search_query)
        )
    
    # Filters
    job_type = request.GET.get('type', '')
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    experience = request.GET.get('experience', '')
    if experience:
        jobs = jobs.filter(experience_level=experience)
    
    location = request.GET.get('location', '')
    if location:
        jobs = jobs.filter(location__icontains=location)
    
    category_slug = request.GET.get('category', '')
    if category_slug:
        jobs = jobs.filter(categories__slug=category_slug)
    
    # Get saved job IDs for authenticated user
    saved_job_ids = []
    if request.user.is_authenticated:
        saved_job_ids = SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True)
    
    # Companies count
    companies_count = jobs.values('company').distinct().count()
    
    # Freelance and fulltime counts
    freelance_count = jobs.filter(job_type='freelance').count()
    fulltime_count = jobs.filter(job_type='fulltime').count()
    
    # Pagination
    paginator = Paginator(jobs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Categories for sidebar
    categories = JobCategory.objects.filter(is_active=True).annotate(
        job_count=Count('jobs', filter=Q(jobs__is_active=True, jobs__expires_at__gt=timezone.now()))
    ).order_by('order', 'name')
    
    # Unique locations for filter
    unique_locations = Job.objects.filter(is_active=True, expires_at__gt=timezone.now()).values_list('location', flat=True).distinct()[:20]
    
    context = {
        'jobs': page_obj,
        'total_jobs': jobs.count(),
        'companies_count': companies_count,
        'freelance_count': freelance_count,
        'fulltime_count': fulltime_count,
        'search_query': search_query,
        'selected_type': job_type,
        'selected_experience': experience,
        'selected_location': location,
        'selected_category': category_slug,
        'categories': categories,
        'unique_locations': unique_locations,
        'saved_job_ids': list(saved_job_ids),  # Pass saved job IDs to template
    }
    return render(request, 'jobs/job_list.html', context)


@login_required
def save_job(request, job_id):
    """Save a job for the logged-in user"""
    if request.method == 'POST':
        try:
            job = get_object_or_404(Job, id=job_id, is_active=True)
            saved_job, created = SavedJob.objects.get_or_create(
                user=request.user,
                job=job
            )
            if created:
                return JsonResponse({'status': 'saved', 'message': 'Job saved successfully'})
            else:
                return JsonResponse({'status': 'already_saved', 'message': 'Job already saved'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def unsave_job(request, job_id):
    """Remove a saved job for the logged-in user"""
    if request.method == 'POST':
        try:
            job = get_object_or_404(Job, id=job_id)
            deleted, _ = SavedJob.objects.filter(user=request.user, job=job).delete()
            if deleted:
                return JsonResponse({'status': 'unsaved', 'message': 'Job removed from saved list'})
            else:
                return JsonResponse({'status': 'not_found', 'message': 'Job not found in saved list'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def job_detail(request, pk):
    """Public job detail page"""
    job = get_object_or_404(Job, pk=pk, is_active=True)
    job.increment_view_count()
    
    # Check if job is saved by user
    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedJob.objects.filter(user=request.user, job=job).exists()
    
    # Get similar jobs (same category or same job type)
    similar_jobs = Job.objects.filter(
        is_active=True,
        expires_at__gt=timezone.now()
    ).exclude(id=job.id)
    
    # Prioritize by category
    if job.categories.exists():
        category_ids = job.categories.values_list('id', flat=True)
        similar_jobs = similar_jobs.filter(categories__id__in=category_ids).distinct()[:4]
    else:
        similar_jobs = similar_jobs.filter(job_type=job.job_type)[:4]
    
    context = {
        'job': job,
        'similar_jobs': similar_jobs,
        'is_saved': is_saved,
    }
    return render(request, 'jobs/job_detail.html', context)


def category_detail(request, slug):
    """Jobs by category"""
    category = get_object_or_404(JobCategory, slug=slug, is_active=True)
    jobs = Job.objects.filter(categories=category, is_active=True, expires_at__gt=timezone.now())
    
    paginator = Paginator(jobs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'jobs': page_obj,
        'total_jobs': jobs.count(),
    }
    return render(request, 'jobs/category_detail.html', context)


@login_required
def dashboard_job_list(request):
    """Dashboard job listing for logged-in users"""
    jobs = Job.objects.filter(is_active=True, expires_at__gt=timezone.now())
    
    search_query = request.GET.get('search', '')
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(company__icontains=search_query)
        )
    
    job_type = request.GET.get('type', '')
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    experience = request.GET.get('experience', '')
    if experience:
        jobs = jobs.filter(experience_level=experience)
    
    location = request.GET.get('location', '')
    if location:
        jobs = jobs.filter(location__icontains=location)
    
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics for dashboard
    total_jobs = jobs.count()
    freelance_count = Job.objects.filter(job_type='freelance', is_active=True, expires_at__gt=timezone.now()).count()
    fulltime_count = Job.objects.filter(job_type='fulltime', is_active=True, expires_at__gt=timezone.now()).count()
    featured_count = Job.objects.filter(is_featured=True, is_active=True, expires_at__gt=timezone.now()).count()
    
    # Unique locations
    unique_locations = Job.objects.filter(is_active=True, expires_at__gt=timezone.now()).values_list('location', flat=True).distinct()
    
    # Get saved job IDs
    saved_job_ids = SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True)
    
    context = {
        'jobs': page_obj,
        'total_jobs': total_jobs,
        'freelance_count': freelance_count,
        'fulltime_count': fulltime_count,
        'featured_count': featured_count,
        'search_query': search_query,
        'selected_type': job_type,
        'selected_experience': experience,
        'selected_location': location,
        'unique_locations': unique_locations,
        'saved_job_ids': list(saved_job_ids),
    }
    return render(request, 'dashboard/jobs_list.html', context)


@login_required
def dashboard_job_detail(request, pk):
    """Dashboard job detail for logged-in users"""
    job = get_object_or_404(Job, pk=pk, is_active=True)
    job.increment_view_count()
    
    # Check if user has already applied
    has_applied = False
    application_status = None
    if request.user.is_authenticated:
        from application.models import Application
        application = Application.objects.filter(user=request.user, job=job).first()
        if application:
            has_applied = True
            application_status = application.status
    
    # Check if job is saved
    is_saved = SavedJob.objects.filter(user=request.user, job=job).exists()
    
    context = {
        'job': job,
        'has_applied': has_applied,
        'application_status': application_status,
        'is_saved': is_saved,
    }
    return render(request, 'dashboard/job_detail.html', context)


@login_required
def saved_jobs(request):
    """View all saved jobs for the logged-in user"""
    saved_jobs = SavedJob.objects.filter(user=request.user).select_related('job').order_by('-saved_at')
    
    # Get application statistics
    from application.models import Application
    applications = Application.objects.filter(user=request.user)
    
    context = {
        'saved_jobs': saved_jobs,
        'saved_jobs_count': saved_jobs.count(),
        'total_applications': applications.count(),
        'pending_applications': applications.filter(status='pending').count(),
    }
    return render(request, 'jobs/saved_jobs.html', context)




