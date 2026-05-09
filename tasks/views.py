from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from .models import Task, TaskComment, TaskAttachment
from .forms import TaskForm, TaskSubmitForm, TaskReviewForm, TaskCommentForm
from wallet.models import UserWallet, Transaction
from notifications.models import create_notification

# ==================== FREELANCER VIEWS ====================

@login_required
def my_tasks(request):
    """Show all tasks assigned to the logged-in freelancer"""
    tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(tasks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Count by status for dashboard
    status_counts = {
        'assigned': Task.objects.filter(assigned_to=request.user, status='assigned').count(),
        'in_progress': Task.objects.filter(assigned_to=request.user, status='in_progress').count(),
        'submitted': Task.objects.filter(assigned_to=request.user, status='submitted').count(),
        'approved': Task.objects.filter(assigned_to=request.user, status='approved').count(),
        'paid': Task.objects.filter(assigned_to=request.user, status='paid').count(),
        'revision_requested': Task.objects.filter(assigned_to=request.user, status='revision_requested').count(),
    }
    
    context = {
        'tasks': page_obj,
        'status_counts': status_counts,
        'current_status': status_filter,
    }
    return render(request, 'tasks/my_tasks.html', context)

@login_required
def task_detail(request, pk):
    """View detailed task information"""
    task = get_object_or_404(Task, pk=pk)
    
    # Ensure user has permission (assigned freelancer or admin)
    if task.assigned_to != request.user and not request.user.is_admin:
        messages.error(request, "You don't have permission to view this task.")
        return redirect('tasks:my_tasks')
    
    # Get comments
    comments = task.comments.filter(is_admin_note=False) if not request.user.is_admin else task.comments.all()
    
    # Handle comment submission
    if request.method == 'POST' and 'comment' in request.POST:
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.user = request.user
            if request.user.is_admin:
                comment.is_admin_note = 'is_admin_note' in request.POST
            comment.save()
            messages.success(request, "Comment added successfully!")
            return redirect('tasks:detail', pk=task.pk)
    
    form = TaskCommentForm()
    
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
        create_notification(
            user=task.assigned_by,
            notification_type='task',
            title='Task Started',
            message=f"{request.user.username} has started working on task: {task.title}",
            link=f'/tasks/{task.id}/'
        )
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
        form = TaskSubmitForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            
            # Handle file attachments
            files = request.FILES.getlist('attachments')
            for file in files:
                TaskAttachment.objects.create(
                    task=task,
                    file=file,
                    filename=file.name,
                    uploaded_by=request.user
                )
            
            if task.submit_task(task.submission_url, task.submission_notes):
                messages.success(request, "Task submitted successfully! Waiting for admin review.")
                create_notification(
                    user=task.assigned_by,
                    notification_type='task',
                    title='Task Submitted',
                    message=f"{request.user.username} has submitted task: {task.title} for review",
                    link=f'/tasks/admin/review/{task.id}/'
                )
                return redirect('tasks:detail', pk=task.pk)
            else:
                messages.error(request, "Failed to submit task. Please try again.")
    else:
        form = TaskSubmitForm(instance=task)
    
    context = {
        'task': task,
        'form': form,
    }
    return render(request, 'tasks/submit_task.html', context)

# ==================== ADMIN VIEWS ====================

@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_tasks(request):
    """Admin view all tasks"""
    tasks = Task.objects.all().order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    freelancer_filter = request.GET.get('freelancer', '')
    job_filter = request.GET.get('job', '')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if freelancer_filter:
        tasks = tasks.filter(assigned_to_id=freelancer_filter)
    if job_filter:
        tasks = tasks.filter(job_id=job_filter)
    
    # Pagination
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
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
@user_passes_test(lambda u: u.is_admin)
def assign_task(request):
    """Admin assign a new task to a freelancer"""
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user
            task.status = 'assigned'
            task.save()
            
            messages.success(request, f"Task '{task.title}' assigned to {task.assigned_to.email}")
            
            # Send notification to freelancer
            create_notification(
                user=task.assigned_to,
                notification_type='task',
                title='New Task Assigned',
                message=f"You have been assigned a new task: {task.title}. Budget: ${task.budget_amount}",
                link=f'/tasks/{task.id}/'
            )
            
            return redirect('tasks:admin_tasks')
    else:
        form = TaskForm()
    
    context = {
        'form': form,
    }
    return render(request, 'tasks/assign_task.html', context)

@login_required
@user_passes_test(lambda u: u.is_admin)
def review_task(request, pk):
    """Admin review submitted task"""
    task = get_object_or_404(Task, pk=pk, status='submitted')
    
    if request.method == 'POST':
        form = TaskReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            feedback = form.cleaned_data.get('feedback', '')
            
            if action == 'approve':
                task.approve_task()
                messages.success(request, f"Task '{task.title}' approved! Ready for payment.")
                create_notification(
                    user=task.assigned_to,
                    notification_type='task',
                    title='Task Approved',
                    message=f"Your task '{task.title}' has been approved! Payment will be processed shortly.",
                    link=f'/tasks/{task.id}/'
                )
                return redirect('tasks:pay_task', pk=task.pk)
                
            elif action == 'request_revision':
                task.request_revision(feedback)
                messages.warning(request, f"Revision requested for '{task.title}'. Feedback sent to freelancer.")
                create_notification(
                    user=task.assigned_to,
                    notification_type='task',
                    title='Revision Requested',
                    message=f"Revision requested for task: {task.title}. Feedback: {feedback[:200]}",
                    link=f'/tasks/{task.id}/'
                )
                
            elif action == 'reject':
                task.reject_task(feedback)
                messages.error(request, f"Task '{task.title}' rejected.")
                create_notification(
                    user=task.assigned_to,
                    notification_type='task',
                    title='Task Rejected',
                    message=f"Your task '{task.title}' has been rejected. Reason: {feedback[:200]}",
                    link=f'/tasks/{task.id}/'
                )
            
            return redirect('tasks:admin_tasks')
    else:
        form = TaskReviewForm()
    
    context = {
        'task': task,
        'form': form,
    }
    return render(request, 'tasks/review_task.html', context)

@login_required
@user_passes_test(lambda u: u.is_admin)
def pay_task(request, pk):
    """Process payment for approved task"""
    task = get_object_or_404(Task, pk=pk, status='approved')
    
    if request.method == 'POST':
        # Add funds to freelancer's wallet
        wallet, created = UserWallet.objects.get_or_create(user=task.assigned_to)
        wallet.add_funds(task.budget_amount)
        
        # Create transaction record
        transaction = Transaction.objects.create(
            user=task.assigned_to,
            transaction_type='task_payment',
            amount=task.budget_amount,
            fee=0,
            net_amount=task.budget_amount,
            description=f"Payment for task: {task.title} (Job: {task.job.title})",
            reference_id=str(task.id)
        )
        
        # Mark task as paid
        task.mark_paid()
        
        messages.success(request, f"${task.budget_amount} has been added to {task.assigned_to.email}'s wallet.")
        
        # Send notification
        create_notification(
            user=task.assigned_to,
            notification_type='payment',
            title='Payment Received',
            message=f"${task.budget_amount} has been added to your wallet for task: {task.title}",
            link='/wallet/'
        )
        
        return redirect('tasks:admin_tasks')
    
    context = {
        'task': task,
        'freelancer_wallet': task.assigned_to.wallet,
    }
    return render(request, 'tasks/pay_task.html', context)

@login_required
@user_passes_test(lambda u: u.is_admin)
def task_analytics(request):
    """Admin analytics dashboard for tasks"""
    from django.db.models import Sum, Count, Avg
    from datetime import datetime, timedelta
    
    # Overall stats
    total_tasks = Task.objects.count()
    total_paid = Task.objects.filter(status='paid').aggregate(Sum('budget_amount'))['budget_amount__sum'] or 0
    avg_completion_time = Task.objects.filter(paid_at__isnull=False).aggregate(
        avg_time=Avg('paid_at' - 'assigned_at')
    )['avg_time']
    
    # Tasks by status
    tasks_by_status = Task.objects.values('status').annotate(count=Count('id'))
    
    # Tasks by month (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    tasks_by_month = Task.objects.filter(created_at__gte=six_months_ago)\
        .extra({'month': "strftime('%%Y-%%m', created_at)"})\
        .values('month')\
        .annotate(count=Count('id'), total_amount=Sum('budget_amount'))
    
    # Top freelancers by earnings
    top_freelancers = Task.objects.filter(status='paid')\
        .values('assigned_to__email', 'assigned_to__username')\
        .annotate(total_earned=Sum('budget_amount'))\
        .order_by('-total_earned')[:10]
    
    context = {
        'total_tasks': total_tasks,
        'total_paid': total_paid,
        'avg_completion_time': avg_completion_time,
        'tasks_by_status': tasks_by_status,
        'tasks_by_month': tasks_by_month,
        'top_freelancers': top_freelancers,
    }
    return render(request, 'tasks/task_analytics.html', context)