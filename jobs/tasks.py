from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Application

@shared_task
def send_application_status_email(application_id):
    """Send email when application status changes"""
    try:
        application = Application.objects.select_related('user', 'job').get(id=application_id)
        status_messages = {
            'approved': 'Your application has been approved! Please complete the quiz.',
            'rejected': 'Your application was not selected for this position.',
            'interview_scheduled': 'Your interview has been scheduled.',
            'hired': 'Congratulations! You have been hired!',
        }
        
        message = status_messages.get(application.status, f'Your application status is now: {application.status}')
        
        send_mail(
            subject=f'Application Update: {application.job.title}',
            message=f'Hi {application.user.first_name or application.user.username},\n\n{message}\n\nBest regards,\nRadiloxRemoteJobs Team',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.user.email],
            fail_silently=True,
        )
        return f"Email sent to {application.user.email}"
    except Application.DoesNotExist:
        return f"Application {application_id} not found"