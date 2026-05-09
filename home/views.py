from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.core.cache import cache
from datetime import datetime, timedelta
import json

from .models import (
    ContactMessage, ContactInfo, SocialLink, 
    FAQ, NewsletterSubscriber, SiteSettings
)
from .forms import ContactForm, NewsletterForm
from jobs.models import Job
from accounts.models import User


# ==================== PUBLIC VIEWS ====================

def home(request):
    """Homepage - Landing page with dynamic content"""
    # Get recent jobs for homepage
    recent_jobs = Job.objects.filter(is_active=True)[:6]
    
    # Get featured jobs
    featured_jobs = Job.objects.filter(is_active=True, is_featured=True)[:3]
    
    # Get statistics
    stats = {
        'jobs_posted': Job.objects.filter(is_active=True).count(),
        'freelancers': User.objects.filter(role='freelancer').count(),
        'zero_commission': 100,
        'active_jobs': Job.objects.filter(is_active=True).count(),
        'total_freelancers': User.objects.filter(role='freelancer').count(),
        'total_earned': '$2.5M+',
        'satisfaction_rate': '98%',
    }
    
    # Get contact info for footer
    contact_info = ContactInfo.objects.first()
    
    # Get social links
    social_links = SocialLink.objects.filter(is_active=True)[:6]
    
    # Pricing plans
    individual_plans = [
        {
            'name': 'Basic', 
            'price': 19, 
            'price_suffix': '/month', 
            'description': 'Perfect for starting out', 
            'is_popular': False, 
            'cta_text': 'Get Started', 
            'cta_url': '/subscriptions/subscribe/',
            'features': ['Apply to jobs', 'Keep 100% earnings', 'Basic support', 'Community access']
        },
        {
            'name': 'Pro', 
            'price': 49, 
            'price_suffix': '/month', 
            'description': 'For serious freelancers', 
            'is_popular': True, 
            'cta_text': 'Get Started', 
            'cta_url': '/subscriptions/subscribe/',
            'features': ['Priority applications', 'Premium support', 'Featured profile', 'Early access to jobs', 'Higher visibility']
        },
        {
            'name': 'Enterprise', 
            'price': 99, 
            'price_suffix': '/month', 
            'description': 'For teams and agencies', 
            'is_popular': False, 
            'cta_text': 'Contact Sales', 
            'cta_url': '/contact/',
            'features': ['Multiple team members', 'API access', 'Dedicated account manager', 'Custom integrations']
        },
    ]
    
    business_plans = [
        {
            'name': 'Starter', 
            'price': 299, 
            'price_suffix': '/month', 
            'description': 'For growing teams', 
            'cta_text': 'Contact Sales', 
            'cta_url': '/contact/',
            'features': ['Up to 10 job posts', 'Team management', 'Analytics dashboard', 'Basic support']
        },
        {
            'name': 'Enterprise', 
            'price': 'Custom', 
            'price_suffix': '', 
            'description': 'For large organizations', 
            'cta_text': 'Contact Sales', 
            'cta_url': '/contact/',
            'features': ['Unlimited job posts', 'White-label solution', 'Dedicated support', 'Custom development', 'SLA guaranteed']
        },
    ]
    
    # Testimonials
    testimonials = [
        {
            'name': 'Sarah Johnson',
            'role': 'Frontend Developer',
            'content': 'RadiloxRemoteJobs changed my career! I found a great remote job and the project-based hiring process was fair and transparent.',
            'rating': 5,
            'avatar': None
        },
        {
            'name': 'Michael Chen',
            'role': 'Full Stack Developer',
            'content': 'The zero commission model is amazing. I keep 100% of what I earn. Best platform for freelancers!',
            'rating': 5,
            'avatar': None
        },
        {
            'name': 'David Wilson',
            'role': 'TechCorp Solutions',
            'content': 'We found exceptional talent through RadiloxRemoteJobs. The project-based vetting saved us countless hours.',
            'rating': 5,
            'avatar': None
        },
    ]
    
    context = {
        'recent_jobs': recent_jobs,
        'featured_jobs': featured_jobs,
        'stats': stats,
        'individual_plans': individual_plans,
        'business_plans': business_plans,
        'testimonials': testimonials,
        'contact_info': contact_info,
        'social_links': social_links,
    }
    
    return render(request, 'home/home.html', context)


def about(request):
    """About page with company information"""
    # Get statistics
    stats = {
        'jobs_posted': Job.objects.filter(is_active=True).count(),
        'freelancers': User.objects.filter(role='freelancer').count(),
        'zero_commission': 100,
        'years_experience': 2,
        'countries': 50,
        'satisfaction_rate': 98,
    }
    
    # Get team members (if you have a TeamMember model)
    team_members = []  # Add your team members here or from database
    
    context = {
        'stats': stats,
        'team_members': team_members,
    }
    return render(request, 'home/about.html', context)


def contact(request):
    """Contact page with dynamic content from database"""
    # Get dynamic contact information from database
    contact_info = ContactInfo.objects.first()
    if not contact_info:
        # Create default if doesn't exist
        contact_info = ContactInfo.objects.create()
    
    # Get active social links
    social_links = SocialLink.objects.filter(is_active=True, show_in_contact=True)
    
    # Get FAQs for the contact page (limit to 5)
    faqs = FAQ.objects.filter(is_active=True)[:5]
    
    # Handle form submission
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save the contact message
            contact_message = form.save(commit=False)
            
            # Capture additional metadata
            if request.user.is_authenticated:
                contact_message.name = request.user.get_full_name() or request.user.username
                contact_message.email = request.user.email
            
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                contact_message.ip_address = x_forwarded_for.split(',')[0]
            else:
                contact_message.ip_address = request.META.get('REMOTE_ADDR')
            
            # Get user agent and referrer
            contact_message.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            contact_message.referred_from = request.META.get('HTTP_REFERER', '')
            
            contact_message.save()
            
            # Send email notification to admin
            send_contact_notification_email(contact_message)
            
            # Send auto-reply to user
            send_contact_autoreply_email(contact_message)
            
            messages.success(request, "Thank you for your message! We'll get back to you within 24 hours.")
            return redirect('home:contact')
        else:
            messages.error(request, "There was an error with your submission. Please check the form and try again.")
    else:
        # Pre-fill form for logged-in users
        if request.user.is_authenticated:
            initial_data = {
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
            }
            form = ContactForm(initial=initial_data)
        else:
            form = ContactForm()
    
    context = {
        'form': form,
        'contact_info': contact_info,
        'social_links': social_links,
        'faqs': faqs,
    }
    return render(request, 'home/contact.html', context)


def faq(request):
    """FAQ page with all FAQs from database"""
    # Get all active FAQs grouped by category
    categories = FAQ.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    
    faqs_by_category = {}
    for category in categories:
        faqs_by_category[category] = FAQ.objects.filter(is_active=True, category=category)
    
    # Get popular FAQs (most viewed)
    popular_faqs = FAQ.objects.filter(is_active=True).order_by('-views')[:5]
    
    # Get contact info for the footer/header
    contact_info = ContactInfo.objects.first()
    
    context = {
        'faqs_by_category': faqs_by_category,
        'total_faqs': FAQ.objects.filter(is_active=True).count(),
        'contact_info': contact_info,
        'popular_faqs': popular_faqs,
    }
    return render(request, 'home/faq.html', context)


def faq_helpful(request, faq_id):
    """AJAX endpoint to mark FAQ as helpful or not helpful"""
    if request.method == 'POST':
        faq = get_object_or_404(FAQ, id=faq_id, is_active=True)
        helpful = request.POST.get('helpful', '')
        
        if helpful == 'yes':
            faq.mark_helpful()
            return JsonResponse({'success': True, 'message': 'Thank you for your feedback!'})
        elif helpful == 'no':
            faq.mark_not_helpful()
            return JsonResponse({'success': True, 'message': 'We appreciate your feedback. We\'ll improve this answer.'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def newsletter_subscribe(request):
    """Handle newsletter subscription"""
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            name = form.cleaned_data.get('name', '')
            
            # Check if already subscribed
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email,
                defaults={'name': name, 'ip_address': get_client_ip(request)}
            )
            
            if created:
                # Send welcome email
                send_newsletter_welcome_email(email, name)
                messages.success(request, "Successfully subscribed to our newsletter!")
            else:
                if not subscriber.is_active:
                    subscriber.is_active = True
                    subscriber.unsubscribed_at = None
                    subscriber.save()
                    messages.success(request, "Successfully re-subscribed to our newsletter!")
                else:
                    messages.info(request, "You are already subscribed to our newsletter.")
            
            return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            messages.error(request, "Please enter a valid email address.")
    
    return redirect('/')


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def terms(request):
    """Terms of Service page"""
    return render(request, 'home/terms.html')


def privacy(request):
    """Privacy Policy page"""
    return render(request, 'home/privacy.html')


def cookies(request):
    """Cookie Policy page"""
    return render(request, 'home/cookies.html')


def accessibility(request):
    """Accessibility Statement page"""
    return render(request, 'home/accessibility.html')


# ==================== EMAIL FUNCTIONS ====================

def send_contact_notification_email(contact_message):
    """Send email notification to admin about new contact message"""
    subject = f"[RadiloxRemoteJobs] New Contact Message: {contact_message.get_subject_display()}"
    
    html_content = render_to_string('emails/contact_notification.html', {
        'message': contact_message,
        'admin_url': getattr(settings, 'SITE_URL', 'https://yourdomain.com'),
    })
    
    text_content = strip_tags(html_content)
    
    admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@radiloxremotejobs.com')
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[admin_email],
        reply_to=[contact_message.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_contact_autoreply_email(contact_message):
    """Send auto-reply email to user who submitted the contact form"""
    subject = "Thank you for contacting RadiloxRemoteJobs"
    
    html_content = render_to_string('emails/contact_autoreply.html', {
        'name': contact_message.name,
        'message': contact_message,
    })
    
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[contact_message.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_reply_email(contact_message, reply_text):
    """Send reply email from admin to user"""
    subject = f"Re: {contact_message.get_subject_display()} - RadiloxRemoteJobs"
    
    html_content = render_to_string('emails/contact_reply.html', {
        'name': contact_message.name,
        'original_message': contact_message.message,
        'reply': reply_text,
    })
    
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[contact_message.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_newsletter_welcome_email(email, name):
    """Send welcome email to new newsletter subscriber"""
    subject = "Welcome to RadiloxRemoteJobs Newsletter!"
    
    html_content = render_to_string('emails/newsletter_welcome.html', {
        'email': email,
        'name': name,
    })
    
    text_content = strip_tags(html_content)
    
    email_msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    email_msg.attach_alternative(html_content, "text/html")
    email_msg.send(fail_silently=True)


# ==================== ERROR HANDLERS ====================

def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, '404.html', status=404)


def custom_500(request):
    """Custom 500 error page"""
    return render(request, '500.html', status=500)


def custom_403(request, exception):
    """Custom 403 error page"""
    return render(request, '403.html', status=403)


def custom_400(request, exception):
    """Custom 400 error page"""
    return render(request, '400.html', status=400)


# ==================== ADMIN VIEWS ====================

@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_contact_messages(request):
    """Admin view to see all contact messages"""
    messages_list = ContactMessage.objects.all()
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        messages_list = messages_list.filter(status=status_filter)
    
    # Filter by subject
    subject_filter = request.GET.get('subject', '')
    if subject_filter:
        messages_list = messages_list.filter(subject=subject_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        messages_list = messages_list.filter(created_at__gte=date_from)
    if date_to:
        messages_list = messages_list.filter(created_at__lte=date_to)
    
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        messages_list = messages_list.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Counts by status
    counts = {
        'new': ContactMessage.objects.filter(status='new').count(),
        'read': ContactMessage.objects.filter(status='read').count(),
        'replied': ContactMessage.objects.filter(status='replied').count(),
        'archived': ContactMessage.objects.filter(status='archived').count(),
        'spam': ContactMessage.objects.filter(status='spam').count(),
        'total': ContactMessage.objects.count(),
    }
    
    # Subject counts
    subject_counts = ContactMessage.objects.values('subject').annotate(count=Count('id'))
    
    context = {
        'messages': page_obj,
        'counts': counts,
        'subject_counts': subject_counts,
        'current_status': status_filter,
        'current_subject': subject_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'admin/contact_messages.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_contact_detail(request, pk):
    """Admin view to see individual contact message details"""
    message = get_object_or_404(ContactMessage, pk=pk)
    
    # Mark as read if it's new
    if message.status == 'new':
        message.mark_as_read()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reply_message = request.POST.get('reply_message', '')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'reply' and reply_message:
            # Send reply email to user
            send_reply_email(message, reply_message)
            message.mark_as_replied(reply_message, request.user)
            messages.success(request, f"Reply sent to {message.email}")
            return redirect('home:admin_contact_detail', pk=message.pk)
        
        elif action == 'resolve':
            message.mark_as_resolved()
            messages.success(request, "Message marked as resolved")
            return redirect('home:admin_contact_messages')
        
        elif action == 'spam':
            message.mark_as_spam()
            messages.success(request, "Message marked as spam")
            return redirect('home:admin_contact_messages')
        
        elif action == 'delete':
            message.delete()
            messages.success(request, "Message deleted")
            return redirect('home:admin_contact_messages')
        
        # Update admin notes
        if admin_notes != message.admin_notes:
            message.admin_notes = admin_notes
            message.save()
            messages.success(request, "Admin notes updated")
    
    context = {
        'message': message,
    }
    return render(request, 'admin/contact_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_faq_manage(request):
    """Admin view to manage FAQs"""
    faqs = FAQ.objects.all().order_by('category', 'order')
    
    if request.method == 'POST':
        # Handle bulk order update
        for faq in faqs:
            order_key = f'order_{faq.id}'
            if order_key in request.POST:
                new_order = int(request.POST[order_key])
                if new_order != faq.order:
                    faq.order = new_order
                    faq.save()
        
        messages.success(request, "FAQ order updated successfully!")
        return redirect('home:admin_faq_manage')
    
    context = {
        'faqs': faqs,
    }
    return render(request, 'admin/faq_manage.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_newsletter_subscribers(request):
    """Admin view to manage newsletter subscribers"""
    subscribers = NewsletterSubscriber.objects.all().order_by('-subscribed_at')
    
    # Filter
    is_active = request.GET.get('active', '')
    if is_active == 'true':
        subscribers = subscribers.filter(is_active=True)
    elif is_active == 'false':
        subscribers = subscribers.filter(is_active=False)
    
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        subscribers = subscribers.filter(
            Q(email__icontains=search_query) |
            Q(name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(subscribers, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Stats
    stats = {
        'total': NewsletterSubscriber.objects.count(),
        'active': NewsletterSubscriber.objects.filter(is_active=True).count(),
        'inactive': NewsletterSubscriber.objects.filter(is_active=False).count(),
        'new_today': NewsletterSubscriber.objects.filter(subscribed_at__date=timezone.now().date()).count(),
    }
    
    context = {
        'subscribers': page_obj,
        'stats': stats,
        'search_query': search_query,
        'active_filter': is_active,
    }
    return render(request, 'admin/newsletter_subscribers.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_export_contact_messages(request):
    """Export contact messages to CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contact_messages_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Email', 'Subject', 'Message', 'Status', 'Created At', 'Replied At', 'IP Address'])
    
    messages = ContactMessage.objects.all()
    
    for msg in messages:
        writer.writerow([
            msg.id,
            msg.name,
            msg.email,
            msg.get_subject_display(),
            msg.message,
            msg.get_status_display(),
            msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            msg.replied_at.strftime('%Y-%m-%d %H:%M:%S') if msg.replied_at else '',
            msg.ip_address or '',
        ])
    
    return response


# ==================== AJAX ENDPOINTS ====================

def ajax_contact_submit(request):
    """AJAX endpoint for contact form submission"""
    from django.http import JsonResponse
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save(commit=False)
            
            # Add metadata
            if request.user.is_authenticated:
                contact_message.name = request.user.get_full_name() or request.user.username
                contact_message.email = request.user.email
            
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                contact_message.ip_address = x_forwarded_for.split(',')[0]
            else:
                contact_message.ip_address = request.META.get('REMOTE_ADDR')
            
            contact_message.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            contact_message.referred_from = request.META.get('HTTP_REFERER', '')
            
            contact_message.save()
            
            # Send emails asynchronously (you can use Celery here)
            send_contact_notification_email(contact_message)
            send_contact_autoreply_email(contact_message)
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for your message! We\'ll get back to you within 24 hours.'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)