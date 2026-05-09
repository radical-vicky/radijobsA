from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import Notification, NotificationPreference, mark_all_as_read
from .utils import send_notification_email_sync


@login_required
def notification_list(request):
    """View all notifications for the logged-in user"""
    
    # Get base queryset
    status_filter = request.GET.get('status', 'active')
    sort_by = request.GET.get('sort', 'newest')
    
    # Filter by status
    if status_filter == 'active':
        notifications = Notification.objects.filter(
            user=request.user
        ).exclude(status='archived').order_by('-created_at')
    elif status_filter == 'archived':
        notifications = Notification.objects.filter(
            user=request.user, 
            status='archived'
        ).order_by('-created_at')
    else:
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Apply sorting
    if sort_by == 'oldest':
        notifications = notifications.order_by('created_at')
    else:
        notifications = notifications.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Counts
    unread_count = Notification.objects.filter(user=request.user, status='unread').count()
    read_count = Notification.objects.filter(user=request.user, status='read').count()
    archived_count = Notification.objects.filter(user=request.user, status='archived').count()
    
    context = {
        'notifications': page_obj,
        'unread_count': unread_count,
        'read_count': read_count,
        'archived_count': archived_count,
        'current_status': status_filter,
        'current_sort': sort_by,
    }
    return render(request, 'notifications/list.html', context)


@login_required
def notification_detail(request, pk):
    """View a single notification detail"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    
    # Mark as read if unread
    if notification.status == 'unread':
        notification.mark_as_read()
    
    # Redirect to the link if provided
    if notification.link:
        return redirect(notification.link)
    
    return render(request, 'notifications/detail.html', {'notification': notification})


@login_required
def mark_read(request, pk):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, "Notification marked as read.")
    next_url = request.GET.get('next', request.META.get('HTTP_REFERER', 'notifications:list'))
    return redirect(next_url)


@login_required
def mark_unread(request, pk):
    """Mark a notification as unread"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_unread()
    
    messages.success(request, "Notification marked as unread.")
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    count = mark_all_as_read(request.user)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'count': count})
    
    messages.success(request, f"{count} notification(s) marked as read.")
    return redirect('notifications:list')


@login_required
def archive_notification(request, pk):
    """Archive a notification"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.archive()
    
    messages.success(request, "Notification archived.")
    return redirect('notifications:list')


@login_required
def unarchive_notification(request, pk):
    """Unarchive a notification (move back to active)"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if notification.status == 'archived':
        notification.status = 'read'
        notification.save()
        messages.success(request, "Notification restored from archive.")
    else:
        messages.warning(request, "Notification is not archived.")
    
    return redirect('notifications:list')


@login_required
def delete_notification(request, pk):
    """Delete a notification permanently"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    
    messages.success(request, "Notification deleted.")
    return redirect('notifications:list')


@login_required
def notification_preferences(request):
    """View and update notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Email preferences
        preferences.email_on_application = request.POST.get('email_on_application') == 'on'
        preferences.email_on_quiz = request.POST.get('email_on_quiz') == 'on'
        preferences.email_on_task = request.POST.get('email_on_task') == 'on'
        preferences.email_on_payment = request.POST.get('email_on_payment') == 'on'
        preferences.email_on_subscription = request.POST.get('email_on_subscription') == 'on'
        preferences.email_on_interview = request.POST.get('email_on_interview') == 'on'
        preferences.email_on_withdrawal = request.POST.get('email_on_withdrawal') == 'on'
        
        # In-app preferences
        preferences.in_app_on_application = request.POST.get('in_app_on_application') == 'on'
        preferences.in_app_on_quiz = request.POST.get('in_app_on_quiz') == 'on'
        preferences.in_app_on_task = request.POST.get('in_app_on_task') == 'on'
        preferences.in_app_on_payment = request.POST.get('in_app_on_payment') == 'on'
        preferences.in_app_on_subscription = request.POST.get('in_app_on_subscription') == 'on'
        preferences.in_app_on_interview = request.POST.get('in_app_on_interview') == 'on'
        preferences.in_app_on_withdrawal = request.POST.get('in_app_on_withdrawal') == 'on'
        
        preferences.save()
        messages.success(request, "Notification preferences updated successfully!")
        return redirect('notifications:preferences')
    
    context = {
        'preferences': preferences,
    }
    return render(request, 'notifications/preferences.html', context)


# ==================== API ENDPOINTS FOR AJAX ====================

@login_required
def api_notification_list(request):
    """API endpoint for fetching notifications (AJAX)"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    unread_count = Notification.objects.filter(user=request.user, status='unread').count()
    
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message[:100] + '...' if len(n.message) > 100 else n.message,
                'notification_type': n.notification_type,
                'is_read': n.status == 'read',
                'time_ago': n.time_ago,
                'link': n.link,
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


@login_required
def api_notification_count(request):
    """API endpoint for getting unread notification count (AJAX)"""
    unread_count = Notification.objects.filter(user=request.user, status='unread').count()
    return JsonResponse({'unread_count': unread_count})


@login_required
@require_http_methods(["POST"])
def api_mark_read(request, pk):
    """API endpoint to mark a notification as read"""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def api_mark_all_read(request):
    """API endpoint to mark all notifications as read"""
    count = mark_all_as_read(request.user)
    return JsonResponse({'success': True, 'count': count})


@login_required
@require_http_methods(["POST"])
def api_archive_notification(request, pk):
    """API endpoint to archive a notification"""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.status = 'archived'
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_unarchive_notification(request, pk):
    """API endpoint to unarchive a notification (move back to active)"""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        if notification.status == 'archived':
            notification.status = 'read'
            notification.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Notification is not archived'}, status=400)
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_archive_all(request):
    """API endpoint to archive all active notifications"""
    try:
        count = Notification.objects.filter(
            user=request.user
        ).exclude(status='archived').update(status='archived')
        return JsonResponse({'success': True, 'count': count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_notification(request, pk):
    """API endpoint to delete a notification"""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.delete()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)