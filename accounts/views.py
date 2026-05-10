from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login as auth_login
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
import json
import csv

from .models import User, UserPaymentMethod
from .forms import UserProfileForm, UserPaymentMethodForm, CustomSignupForm
from jobs.models import Job
from application.models import Application
from tasks.models import Task
from wallet.models import UserWallet, Transaction, WithdrawalRequest
from notifications.models import Notification
from notifications.models import create_notification


# ==================== DASHBOARD VIEWS ====================

@login_required
def dashboard(request):
    """Main dashboard redirects based on user role"""
    if request.user.role == 'admin':
        return redirect('accounts:admin_dashboard')
    elif request.user.role == 'freelancer':
        return redirect('accounts:freelancer_dashboard')
    else:
        return redirect('accounts:applicant_dashboard')


@login_required
def admin_dashboard(request):
    """Admin dashboard with platform statistics"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admin only.")
        return redirect('accounts:dashboard')
    
    today = timezone.now().date()
    thirty_days_ago = today - timezone.timedelta(days=30)
    
    total_users = User.objects.count()
    total_applicants = User.objects.filter(role='applicant').count()
    total_freelancers = User.objects.filter(role='freelancer').count()
    active_jobs = Job.objects.filter(is_active=True).count()
    total_jobs = Job.objects.count()
    pending_applications = Application.objects.filter(status='pending').count()
    total_applications = Application.objects.count()
    
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='paid').count()
    pending_tasks = Task.objects.filter(status='assigned').count()
    
    total_withdrawals = WithdrawalRequest.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    withdrawal_fees = WithdrawalRequest.objects.filter(status='completed').aggregate(Sum('fee'))['fee__sum'] or 0
    subscription_revenue = 0
    
    recent_applications = Application.objects.all().select_related('user', 'job').order_by('-created_at')[:10]
    recent_users = User.objects.all().order_by('-date_joined')[:10]
    recent_withdrawals = WithdrawalRequest.objects.filter(status='pending').order_by('-requested_at')[:10]
    
    monthly_user_trend = []
    monthly_job_trend = []
    for i in range(6):
        month_start = timezone.now() - timezone.timedelta(days=30 * i)
        month_users = User.objects.filter(date_joined__month=month_start.month, date_joined__year=month_start.year).count()
        month_jobs = Job.objects.filter(created_at__month=month_start.month, created_at__year=month_start.year).count()
        monthly_user_trend.append({'month': month_start.strftime('%b'), 'count': month_users})
        monthly_job_trend.append({'month': month_start.strftime('%b'), 'count': month_jobs})
    
    new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    new_applicants_30d = User.objects.filter(role='applicant', date_joined__gte=thirty_days_ago).count()
    new_freelancers_30d = User.objects.filter(role='freelancer', date_joined__gte=thirty_days_ago).count()
    
    trending_jobs = Job.objects.filter(is_active=True).order_by('-view_count')[:5]
    recent_notifications = Notification.objects.filter(user=request.user)[:5]
    
    context = {
        'total_users': total_users,
        'total_applicants': total_applicants,
        'total_freelancers': total_freelancers,
        'active_jobs': active_jobs,
        'total_jobs': total_jobs,
        'pending_applications': pending_applications,
        'total_applications': total_applications,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'completion_rate': int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0,
        'total_withdrawals': total_withdrawals,
        'withdrawal_fees': withdrawal_fees,
        'subscription_revenue': subscription_revenue,
        'total_revenue': subscription_revenue + withdrawal_fees,
        'recent_applications': recent_applications,
        'recent_users': recent_users,
        'recent_withdrawals': recent_withdrawals,
        'monthly_user_trend': json.dumps(list(reversed(monthly_user_trend))),
        'monthly_job_trend': json.dumps(list(reversed(monthly_job_trend))),
        'new_users_30d': new_users_30d,
        'new_applicants_30d': new_applicants_30d,
        'new_freelancers_30d': new_freelancers_30d,
        'trending_jobs': trending_jobs,
        'recent_notifications': recent_notifications,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def freelancer_dashboard(request):
    """Freelancer dashboard with tasks and earnings"""
    if request.user.role != 'freelancer':
        messages.error(request, "Access denied. Freelancer only.")
        return redirect('accounts:dashboard')
    
    wallet, created = UserWallet.objects.get_or_create(user=request.user)
    
    assigned_tasks = Task.objects.filter(assigned_to=request.user, status='assigned')
    in_progress_tasks = Task.objects.filter(assigned_to=request.user, status='in_progress')
    submitted_tasks = Task.objects.filter(assigned_to=request.user, status='submitted')
    completed_tasks = Task.objects.filter(assigned_to=request.user, status='paid')
    
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    pending_withdrawals = WithdrawalRequest.objects.filter(user=request.user, status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    total_withdrawn = wallet.total_withdrawn
    
    context = {
        'wallet': wallet,
        'assigned_tasks': assigned_tasks,
        'in_progress_tasks': in_progress_tasks,
        'submitted_tasks': submitted_tasks,
        'completed_tasks': completed_tasks,
        'recent_transactions': recent_transactions,
        'pending_withdrawals': pending_withdrawals,
        'total_withdrawn': total_withdrawn,
        'assigned_count': assigned_tasks.count(),
        'in_progress_count': in_progress_tasks.count(),
        'submitted_count': submitted_tasks.count(),
        'completed_count': completed_tasks.count(),
    }
    return render(request, 'dashboard/freelancer_dashboard.html', context)


@login_required
def applicant_dashboard(request):
    """Applicant dashboard with applications and job search"""
    if request.user.role != 'applicant':
        messages.error(request, "Access denied. Applicant only.")
        return redirect('accounts:dashboard')
    
    applications = Application.objects.filter(user=request.user).select_related('job').order_by('-created_at')
    
    total_applications = applications.count()
    pending_applications = applications.filter(status='pending').count()
    shortlisted_applications = applications.filter(status='shortlisted').count()
    approved_applications = applications.filter(status='approved').count()
    interview_applications = applications.filter(status='interview_scheduled').count()
    hired_applications = applications.filter(status='hired').count()
    rejected_applications = applications.filter(status='rejected').count()
    
    recent_applications = applications[:10]
    
    upcoming_interviews = applications.filter(
        interview_scheduled_at__isnull=False,
        interview_scheduled_at__gte=timezone.now()
    ).order_by('interview_scheduled_at')[:5]
    
    if applications.exists():
        skills_used = []
        for app in applications[:5]:
            if app.job.skills_required:
                skills_used.extend(app.job.skills_required)
        
        if skills_used:
            recommended_jobs = Job.objects.filter(
                is_active=True,
                skills_required__overlap=skills_used[:5]
            ).exclude(id__in=applications.values_list('job_id', flat=True))[:6]
        else:
            recommended_jobs = Job.objects.filter(is_active=True).exclude(
                id__in=applications.values_list('job_id', flat=True)
            )[:6]
    else:
        recommended_jobs = Job.objects.filter(is_active=True)[:6]
    
    context = {
        'applications': applications,
        'recent_applications': recent_applications,
        'has_active_subscription': request.user.has_active_subscription,
        'subscription_expires_at': request.user.subscription_expires_at,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'shortlisted_applications': shortlisted_applications,
        'approved_applications': approved_applications,
        'interview_applications': interview_applications,
        'hired_applications': hired_applications,
        'rejected_applications': rejected_applications,
        'upcoming_interviews': upcoming_interviews,
        'recommended_jobs': recommended_jobs,
    }
    return render(request, 'dashboard/applicant_dashboard.html', context)


# ==================== PROFILE VIEWS ====================

@login_required
def profile(request):
    """User profile view and edit"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserProfileForm(instance=request.user)
    
    total_applications = 0
    hired_count = 0
    completed_tasks = 0
    in_progress_tasks = 0
    total_earned = 0
    total_users = 0
    active_jobs = 0
    pending_applications = 0
    recent_applications = []
    assigned_tasks = []
    wallet = None
    recent_notifications = []
    
    if request.user.is_applicant:
        total_applications = Application.objects.filter(user=request.user).count()
        hired_count = Application.objects.filter(user=request.user, status='hired').count()
        recent_applications = Application.objects.filter(user=request.user).select_related('job').order_by('-created_at')[:5]
        
    elif request.user.is_freelancer:
        wallet, created = UserWallet.objects.get_or_create(user=request.user)
        total_earned = wallet.total_earned
        completed_tasks = Task.objects.filter(assigned_to=request.user, status='paid').count()
        in_progress_tasks = Task.objects.filter(assigned_to=request.user, status='in_progress').count()
        assigned_tasks = Task.objects.filter(assigned_to=request.user, status='assigned')[:5]
        
    elif request.user.is_superuser:
        total_users = User.objects.count()
        active_jobs = Job.objects.filter(is_active=True).count()
        pending_applications = Application.objects.filter(status='pending').count()
    
    recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'form': form,
        'user': request.user,
        'total_applications': total_applications,
        'hired_count': hired_count,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'total_earned': total_earned,
        'total_users': total_users,
        'active_jobs': active_jobs,
        'pending_applications': pending_applications,
        'recent_applications': recent_applications,
        'assigned_tasks': assigned_tasks,
        'wallet': wallet,
        'recent_notifications': recent_notifications,
        'avatar_url': request.user.avatar.url if request.user.avatar else None,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """Edit user profile page"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def payment_methods(request):
    """Manage user payment methods"""
    methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True)
    
    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        is_default = request.POST.get('is_default') == 'on'
        
        payment_method = UserPaymentMethod(
            user=request.user,
            payment_type=payment_type,
            is_default=is_default,
            is_active=True
        )
        
        if payment_type == 'paypal':
            payment_method.account_email = request.POST.get('paypal_email', '')
            payment_method.last_four = ''
            
        elif payment_type == 'mpesa':
            payment_method.phone_number = request.POST.get('phone_number', '')
            payment_method.last_four = ''
            
        elif payment_type == 'bank_account':
            payment_method.bank_name = request.POST.get('bank_name', '')
            payment_method.bank_account_name = request.POST.get('account_name', '')
            payment_method.bank_account_number = request.POST.get('account_number', '')
            payment_method.bank_swift_code = request.POST.get('swift_code', '')
            payment_method.last_four = request.POST.get('account_number', '')[-4:] if request.POST.get('account_number') else ''
            
        elif payment_type == 'credit_card' or payment_type == 'debit_card':
            payment_method.last_four = request.POST.get('last_four', '')
            payment_method.card_holder_name = request.POST.get('card_holder_name', '')
            payment_method.expiry_month = request.POST.get('expiry_month')
            payment_method.expiry_year = request.POST.get('expiry_year')
        
        if payment_type == 'paypal' and not payment_method.account_email:
            messages.error(request, 'PayPal email is required')
            return redirect('accounts:payment_methods')
        elif payment_type == 'mpesa' and not payment_method.phone_number:
            messages.error(request, 'M-Pesa phone number is required')
            return redirect('accounts:payment_methods')
        elif payment_type == 'bank_account' and not payment_method.bank_account_number:
            messages.error(request, 'Bank account number is required')
            return redirect('accounts:payment_methods')
        
        if is_default or not methods.exists():
            UserPaymentMethod.objects.filter(user=request.user).update(is_default=False)
            payment_method.is_default = True
        
        payment_method.save()
        messages.success(request, f"{dict(UserPaymentMethod.PAYMENT_TYPES).get(payment_type, payment_type)} added successfully!")
        return redirect('accounts:payment_methods')
    
    context = {'methods': methods}
    return render(request, 'accounts/payment_methods.html', context)


@login_required
def set_default_payment_method(request, pk):
    """Set a payment method as default"""
    payment_method = get_object_or_404(UserPaymentMethod, pk=pk, user=request.user)
    
    UserPaymentMethod.objects.filter(user=request.user).update(is_default=False)
    
    payment_method.is_default = True
    payment_method.save()
    
    messages.success(request, "Default payment method updated!")
    return redirect('accounts:payment_methods')


@login_required
def delete_payment_method(request, pk):
    """Delete a payment method"""
    payment_method = get_object_or_404(UserPaymentMethod, pk=pk, user=request.user)
    payment_method.delete()
    
    if not UserPaymentMethod.objects.filter(user=request.user, is_default=True).exists():
        next_method = UserPaymentMethod.objects.filter(user=request.user).first()
        if next_method:
            next_method.is_default = True
            next_method.save()
    
    messages.success(request, "Payment method deleted successfully!")
    return redirect('accounts:payment_methods')


# ==================== ADMIN USER MANAGEMENT ====================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    """Admin: List all users with filters"""
    users = User.objects.all()
    
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    subscription_filter = request.GET.get('subscription', '')
    if subscription_filter == 'active':
        users = users.filter(is_subscription_active=True)
    elif subscription_filter == 'inactive':
        users = users.filter(is_subscription_active=False)
    
    search_query = request.GET.get('q', '')
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    stats = {
        'total': User.objects.count(),
        'admins': User.objects.filter(role='admin').count(),
        'applicants': User.objects.filter(role='applicant').count(),
        'freelancers': User.objects.filter(role='freelancer').count(),
        'active_subscriptions': User.objects.filter(is_subscription_active=True).count(),
    }
    
    context = {
        'users': page_obj,
        'stats': stats,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'subscription_filter': subscription_filter,
        'search_query': search_query,
    }
    return render(request, 'admin/users_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_detail(request, pk):
    """Admin: View user details"""
    user_detail = get_object_or_404(User, pk=pk)
    
    wallet, created = UserWallet.objects.get_or_create(user=user_detail)
    applications = Application.objects.filter(user=user_detail).select_related('job')
    tasks = Task.objects.filter(assigned_to=user_detail)
    transactions = Transaction.objects.filter(user=user_detail).order_by('-created_at')[:20]
    payment_methods = UserPaymentMethod.objects.filter(user=user_detail)
    
    context = {
        'user_detail': user_detail,
        'wallet': wallet,
        'applications': applications,
        'tasks': tasks,
        'transactions': transactions,
        'payment_methods': payment_methods,
        'applications_count': applications.count(),
        'tasks_count': tasks.count(),
        'tasks_completed': tasks.filter(status='paid').count(),
    }
    return render(request, 'admin/user_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_toggle_status(request, pk):
    """Admin: Activate/deactivate user"""
    user_obj = get_object_or_404(User, pk=pk)
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    
    status = "activated" if user_obj.is_active else "deactivated"
    messages.success(request, f"User '{user_obj.email}' has been {status}.")
    
    if not user_obj.is_active:
        send_account_suspended_email(user_obj)
    
    return redirect('accounts:user_detail', pk=pk)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_change_role(request, pk):
    """Admin: Change user role"""
    if request.method == 'POST':
        user_obj = get_object_or_404(User, pk=pk)
        new_role = request.POST.get('role')
        
        if new_role in dict(User.ROLE_CHOICES):
            old_role = user_obj.role
            user_obj.role = new_role
            user_obj.save()
            
            messages.success(request, f"User '{user_obj.email}' role changed from {old_role} to {new_role}.")
            
            create_notification(
                user=user_obj,
                notification_type='system',
                title='Role Updated',
                message=f"Your account role has been changed to {new_role}. Please refresh your dashboard.",
                link='/dashboard/'
            )
    
    return redirect('accounts:user_detail', pk=pk)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_export(request):
    """Admin: Export users to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Email', 'Full Name', 'Role', 'Active', 'Subscription', 'Joined Date', 'Last Login'])
    
    users = User.objects.all()
    for user in users:
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.get_full_name(),
            user.role,
            'Yes' if user.is_active else 'No',
            'Yes' if user.has_active_subscription else 'No',
            user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
        ])
    
    return response


# ==================== HELPER FUNCTIONS ====================

def send_account_suspended_email(user):
    """Send email notification when account is suspended"""
    subject = "Your RadiloxRemoteJobs account has been suspended"
    message = f"""
Dear {user.get_full_name() or user.username},

Your RadiloxRemoteJobs account has been suspended. If you believe this is an error, please contact support.

Regards,
RadiloxRemoteJobs Team
"""
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


# ==================== AJAX ENDPOINTS ====================

@login_required
def get_notifications_ajax(request):
    """AJAX: Get unread notifications count"""
    unread_count = Notification.objects.filter(user=request.user, status='unread').count()
    return JsonResponse({'unread_count': unread_count})


@login_required
def mark_all_notifications_read(request):
    """AJAX: Mark all notifications as read"""
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, status='unread').update(
            status='read',
            read_at=timezone.now()
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


# ==================== ERROR HANDLERS ====================

def custom_403(request, exception):
    return render(request, '403.html', status=403)


def custom_400(request, exception):
    return render(request, '400.html', status=400)