from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Sum  # Add Sum here
from django.conf import settings
from .models import Task, TaskComment, TaskAttachment
from .forms import TaskForm, TaskCommentForm
from wallet.models import UserWallet, Transaction
from notifications.models import Notification


# ==================== FREELANCER VIEWS ====================

@login_required
def my_tasks(request):
    """Show all tasks assigned to the logged-in freelancer, grouped by status"""
    all_tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')
    
    assigned_tasks = all_tasks.filter(status='assigned')
    in_progress_tasks = all_tasks.filter(status='in_progress')
    submitted_tasks = all_tasks.filter(status='submitted')
    completed_tasks = all_tasks.filter(status__in=['approved', 'paid'])
    
    # History tasks (completed, paid, rejected)
    history_tasks = all_tasks.filter(status__in=['paid', 'approved', 'rejected']).order_by('-paid_at', '-approved_at', '-created_at')
    
    # Statistics for history
    total_paid_tasks = all_tasks.filter(status='paid').count()
    total_rejected_tasks = all_tasks.filter(status='rejected').count()
    total_earnings = all_tasks.filter(status='paid').aggregate(Sum('budget_amount'))['budget_amount__sum'] or 0
    
    assigned_count = assigned_tasks.count()
    in_progress_count = in_progress_tasks.count()
    submitted_count = submitted_tasks.count()
    completed_count = completed_tasks.count()
    
    context = {
        'assigned_tasks': assigned_tasks,
        'in_progress_tasks': in_progress_tasks,
        'submitted_tasks': submitted_tasks,
        'completed_tasks': completed_tasks,
        'history_tasks': history_tasks,
        'assigned_count': assigned_count,
        'in_progress_count': in_progress_count,
        'submitted_count': submitted_count,
        'completed_count': completed_count,
        'total_paid_tasks': total_paid_tasks,
        'total_rejected_tasks': total_rejected_tasks,
        'total_earnings': total_earnings,
    }
    return render(request, 'tasks/my_tasks.html', context)


@login_required
def task_detail(request, pk):
    """View detailed task information"""
    task = get_object_or_404(Task, pk=pk)
    
    if task.assigned_to != request.user and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this task.")
        return redirect('tasks:my_tasks')
    
    comments = task.comments.filter(is_admin_note=False) if not request.user.is_superuser else task.comments.all()
    
    if request.method == 'POST' and 'comment' in request.POST:
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.user = request.user
            if request.user.is_superuser:
                comment.is_admin_note = 'is_admin_note' in request.POST
            comment.save()
            messages.success(request, "Comment added successfully!")
            return redirect('tasks:detail', pk=task.pk)
    
    form = TaskCommentForm()
    
    if request.method == 'POST' and 'action' in request.POST:
        action = request.POST.get('action')
        
        if action == 'start' and task.status == 'assigned':
            if task.start_task():
                messages.success(request, f"Task '{task.title}' marked as in progress. Good luck!")
            else:
                messages.error(request, "Unable to start this task.")
            return redirect('tasks:detail', pk=task.pk)
        
        elif action == 'submit':
            submission_url = request.POST.get('submission_url', '')
            submission_notes = request.POST.get('submission_notes', '')
            
            files = request.FILES.getlist('attachments')
            for file in files:
                TaskAttachment.objects.create(
                    task=task,
                    file=file,
                    filename=file.name,
                    uploaded_by=request.user
                )
            
            if task.submit_task(submission_url, submission_notes):
                messages.success(request, "Task submitted successfully! Waiting for admin review.")
            else:
                messages.error(request, "Failed to submit task.")
            return redirect('tasks:detail', pk=task.pk)
    
    context = {
        'task': task,
        'comments': comments,
        'form': form,
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def start_task(request, pk):
    """Mark task as in progress"""
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    
    if task.start_task():
        messages.success(request, f"Task '{task.title}' marked as in progress. Good luck!")
    else:
        messages.error(request, "Unable to start this task. It may already be in progress.")
    
    return redirect('tasks:detail', pk=task.pk)


@login_required
def submit_task(request, pk):
    """Submit completed task for review"""
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    
    if task.status not in ['assigned', 'in_progress', 'revision_requested']:
        messages.error(request, "You cannot submit this task at this time.")
        return redirect('tasks:detail', pk=task.pk)
    
    if request.method == 'POST':
        submission_url = request.POST.get('submission_url', '')
        submission_notes = request.POST.get('submission_notes', '')
        
        files = request.FILES.getlist('attachments')
        for file in files:
            TaskAttachment.objects.create(
                task=task,
                file=file,
                filename=file.name,
                uploaded_by=request.user
            )
        
        if task.submit_task(submission_url, submission_notes):
            messages.success(request, "Task submitted successfully! Waiting for admin review.")
            return redirect('tasks:detail', pk=task.pk)
        else:
            messages.error(request, "Failed to submit task. Please try again.")
    
    context = {
        'task': task,
    }
    return render(request, 'tasks/submit_task.html', context)


# ==================== ADMIN VIEWS ====================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_tasks(request):
    """Admin view all tasks"""
    tasks = Task.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status', '')
    freelancer_filter = request.GET.get('freelancer', '')
    job_filter = request.GET.get('job', '')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if freelancer_filter:
        tasks = tasks.filter(assigned_to_id=freelancer_filter)
    if job_filter:
        tasks = tasks.filter(job_id=job_filter)
    
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    from accounts.models import User
    from jobs.models import Job
    freelancers = User.objects.filter(role='freelancer')
    jobs = Job.objects.filter(is_active=True)
    
    context = {
        'tasks': page_obj,
        'freelancers': freelancers,
        'jobs': jobs,
        'selected_status': status_filter,
        'selected_freelancer': freelancer_filter,
        'selected_job': job_filter,
        'status_counts': {
            'assigned': Task.objects.filter(status='assigned').count(),
            'in_progress': Task.objects.filter(status='in_progress').count(),
            'submitted': Task.objects.filter(status='submitted').count(),
            'approved': Task.objects.filter(status='approved').count(),
            'paid': Task.objects.filter(status='paid').count(),
        }
    }
    return render(request, 'tasks/admin_tasks.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def assign_task(request):
    """Admin assign a new task to a freelancer"""
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user
            task.status = 'assigned'
            task.save()
            
            task.assign_task(request.user)
            
            messages.success(request, f"Task '{task.title}' assigned to {task.assigned_to.email}")
            return redirect('tasks:admin_tasks')
    else:
        form = TaskForm()
    
    context = {
        'form': form,
    }
    return render(request, 'tasks/assign_task.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def review_task(request, pk):
    """Admin review submitted task"""
    task = get_object_or_404(Task, pk=pk, status='submitted')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        feedback = request.POST.get('feedback', '')
        
        if action == 'approve':
            task.approve_task()
            messages.success(request, f"Task '{task.title}' approved! Ready for payment.")
            
        elif action == 'revision':
            task.request_revision(feedback)
            messages.warning(request, f"Revision requested for '{task.title}'. Feedback sent to freelancer.")
            
        elif action == 'reject':
            task.reject_task(feedback)
            messages.error(request, f"Task '{task.title}' rejected.")
        
        return redirect('tasks:admin_tasks')
    
    context = {
        'task': task,
    }
    return render(request, 'tasks/review_task.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def pay_task(request, pk):
    """Process payment for approved task"""
    task = get_object_or_404(Task, pk=pk, status='approved')
    
    if request.method == 'POST':
        # This will automatically update wallet, create transaction, send notification and email
        if task.mark_paid():
            messages.success(request, f"✓ ${task.budget_amount} has been added to {task.assigned_to.email}'s wallet.")
            messages.success(request, f"✓ Transaction created and notification sent.")
        else:
            messages.error(request, "Failed to process payment.")
        
        return redirect('tasks:admin_tasks')
    
    context = {'task': task}
    return render(request, 'tasks/pay_task.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def task_analytics(request):
    """Admin analytics dashboard for tasks"""
    from django.db.models import Sum, Count
    from datetime import timedelta
    
    total_tasks = Task.objects.count()
    total_paid = Task.objects.filter(status='paid').aggregate(Sum('budget_amount'))['budget_amount__sum'] or 0
    total_freelancers = Task.objects.values('assigned_to').distinct().count()
    
    tasks_by_status = Task.objects.values('status').annotate(count=Count('id'))
    six_months_ago = timezone.now() - timedelta(days=180)
    tasks_by_month = Task.objects.filter(created_at__gte=six_months_ago)
    
    top_freelancers = Task.objects.filter(status='paid')\
        .values('assigned_to__username', 'assigned_to__email')\
        .annotate(total_earned=Sum('budget_amount'))\
        .order_by('-total_earned')[:10]
    
    context = {
        'total_tasks': total_tasks,
        'total_paid': total_paid,
        'total_freelancers': total_freelancers,
        'tasks_by_status': tasks_by_status,
        'tasks_by_month': tasks_by_month,
        'top_freelancers': top_freelancers,
    }
    return render(request, 'tasks/task_analytics.html', context)