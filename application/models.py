from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse


class Application(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('shortlisted', 'Shortlisted - Under Review'),
        ('approved', 'Approved for Interview'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_completed', 'Interview Completed'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='applications')
    
    # Application details
    cover_letter = models.TextField()
    repository_link = models.URLField(help_text="GitHub/GitLab repository link")
    deployment_link = models.URLField(blank=True, null=True, help_text="Live demo link (optional)")
    test_credentials = models.TextField(blank=True, null=True, help_text="Test credentials for the deployed site")
    project_notes = models.TextField(blank=True, null=True, help_text="Additional notes about the project")
    
    # Project files
    project_file = models.FileField(upload_to='applications/projects/', blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    feedback = models.TextField(blank=True, null=True, help_text="Feedback for rejected applications")
    
    # Interview
    interview_scheduled_at = models.DateTimeField(blank=True, null=True)
    interview_link = models.CharField(max_length=500, blank=True, null=True)
    interview_completed = models.BooleanField(default=False)
    
    # Hiring
    hired_at = models.DateTimeField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True, help_text="Job start date")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.job.title} - {self.get_status_display()}"
    
    def get_absolute_url(self):
        return reverse('application:detail', args=[self.id])
    
    def shortlist(self, reviewer):
        """Shortlist the application after project review"""
        self.status = 'shortlisted'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save()
        
        from notifications.utils import create_notification
        create_notification(
            user=self.user,
            notification_type='application',
            title='Application Shortlisted',
            message=f'Congratulations! Your application for {self.job.title} has been shortlisted. Your project is being reviewed.',
            link=f'/applications/detail/{self.id}/'
        )
        
        self._send_email('shortlisted')
        return True
    
    def approve_for_interview(self, reviewer):
        """Approve for interview after project meets requirements"""
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save()
        
        from notifications.utils import create_notification
        create_notification(
            user=self.user,
            notification_type='application',
            title='Congratulations! You Qualify for Interview',
            message=f'Great news! Your project for {self.job.title} has been reviewed and approved. You now qualify for the interview stage.',
            link=f'/applications/detail/{self.id}/'
        )
        
        self._send_email('approved')
        return True
    
    def reject(self, reviewer, feedback):
        """Reject application with feedback"""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.feedback = feedback
        self.save()
        
        from notifications.utils import create_notification
        create_notification(
            user=self.user,
            notification_type='application',
            title='Application Update - Not Selected',
            message=f'Thank you for applying to {self.job.title}. Unfortunately, your application was not selected at this time.',
            link=f'/applications/detail/{self.id}/'
        )
        
        self._send_email('rejected')
        return True
    
    def schedule_interview(self, interview_datetime, zoom_link=None):
        """Schedule Zoom interview - creates real Zoom meeting and ZoomMeeting record"""
        from zoom_integration.services import create_meeting
        from zoom_integration.models import ZoomMeeting
        
        # If no zoom_link provided, create a real Zoom meeting
        if not zoom_link:
            meeting = create_meeting(
                topic=f"Interview: {self.job.title} - {self.user.username}",
                start_time=interview_datetime,
                duration_minutes=60
            )
            
            if meeting.get('success'):
                zoom_link = meeting['join_url']
                meeting_id = meeting.get('meeting_id')
                print(f"✓ Real Zoom meeting created: {zoom_link}")
                
                # Create ZoomMeeting record
                ZoomMeeting.objects.create(
                    user=self.user,
                    application=self,
                    meeting_id=meeting_id,
                    topic=f"Interview: {self.job.title}",
                    meeting_type='interview',
                    start_time=interview_datetime,
                    duration_minutes=60,
                    join_url=zoom_link,
                    status='scheduled'
                )
            else:
                # Fallback - still create a record with fallback link
                zoom_link = zoom_link or f"https://zoom.us/j/fallback-{self.id}"
                print(f"⚠️ Zoom meeting creation failed, using fallback: {zoom_link}")
                
                # Create ZoomMeeting record with fallback
                ZoomMeeting.objects.create(
                    user=self.user,
                    application=self,
                    meeting_id=f"fallback-{self.id}",
                    topic=f"Interview: {self.job.title}",
                    meeting_type='interview',
                    start_time=interview_datetime,
                    duration_minutes=60,
                    join_url=zoom_link,
                    status='scheduled'
                )
        else:
            # Zoom link provided directly - create record
            ZoomMeeting.objects.create(
                user=self.user,
                application=self,
                meeting_id=f"manual-{self.id}",
                topic=f"Interview: {self.job.title}",
                meeting_type='interview',
                start_time=interview_datetime,
                duration_minutes=60,
                join_url=zoom_link,
                status='scheduled'
            )
        
        self.status = 'interview_scheduled'
        self.interview_scheduled_at = interview_datetime
        self.interview_link = zoom_link
        self.save()
        
        # Create in-app notification
        from notifications.utils import create_notification
        create_notification(
            user=self.user,
            notification_type='interview',
            title='Interview Scheduled',
            message=f'Your interview for {self.job.title} has been scheduled for {interview_datetime.strftime("%B %d, %Y at %H:%M")}. Please use the provided Zoom link to join.',
            link=zoom_link
        )
        
        # Send email
        self._send_interview_email(interview_datetime, zoom_link)
        
        return True
    
    def complete_interview(self):
        """Mark interview as completed"""
        self.status = 'interview_completed'
        self.interview_completed = True
        self.save()
        
        # Update ZoomMeeting status
        try:
            from zoom_integration.models import ZoomMeeting
            meeting = ZoomMeeting.objects.filter(application=self, status='scheduled').first()
            if meeting:
                meeting.status = 'completed'
                meeting.save()
        except:
            pass
        
        from notifications.utils import create_notification
        create_notification(
            user=self.user,
            notification_type='interview',
            title='Interview Completed',
            message=f'Your interview for {self.job.title} has been marked as completed. Our team will review and get back to you soon.',
            link=f'/applications/detail/{self.id}/'
        )
        
        self._send_interview_completed_email()
        return True
    
    def hire(self, start_date):
        """Hire the applicant"""
        self.status = 'hired'
        self.hired_at = timezone.now()
        self.start_date = start_date
        self.save()
        
        from notifications.utils import create_notification
        create_notification(
            user=self.user,
            notification_type='application',
            title='You\'re Hired!',
            message=f'Congratulations! You have been hired for {self.job.title}! Your start date is {start_date.strftime("%B %d, %Y")}.',
            link=f'/applications/detail/{self.id}/'
        )
        
        self._send_hiring_email(start_date)
        return True
    
    def _send_email(self, email_type):
        """Send email notifications immediately"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        if email_type == 'shortlisted':
            subject = f"Application Shortlisted - {self.job.title}"
            message = f"""
Dear {self.user.get_full_name() or self.user.username},

Congratulations! Your application for the position of {self.job.title} has been shortlisted.

Our team is reviewing your project submission. We will notify you once the review is complete.

Status: Shortlisted
Position: {self.job.title}
Company: {self.job.company}

Thank you for your interest.

Best regards,
RadiloxRemoteJobs Team
"""
        elif email_type == 'approved':
            subject = f"You Qualify for Interview - {self.job.title}"
            message = f"""
Dear {self.user.get_full_name() or self.user.username},

Great news! Your project submission for {self.job.title} has been reviewed and approved.

You have qualified for the interview stage. You will receive a separate email with the Zoom interview link and scheduling details.

Position: {self.job.title}
Company: {self.job.company}

Prepare to present your project during the Zoom interview.

Best regards,
RadiloxRemoteJobs Team
"""
        elif email_type == 'rejected':
            subject = f"Application Update - {self.job.title}"
            message = f"""
Dear {self.user.get_full_name() or self.user.username},

Thank you for your interest in the {self.job.title} position at {self.job.company}.

After careful review of your application and project, we regret to inform you that we have decided to move forward with other candidates at this time.

Feedback: {self.feedback}

We encourage you to apply for other positions that match your skills.

Best regards,
RadiloxRemoteJobs Team
"""
        else:
            return
        
        try:
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
                fail_silently=False
            )
            if sent:
                print(f"✓ Email sent to {self.user.email} for {email_type}")
            return sent
        except Exception as e:
            print(f"✗ Email failed to {self.user.email}: {str(e)}")
            return False
    
    def _send_interview_email(self, interview_datetime, zoom_link):
        """Send interview invitation email immediately"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Interview Invitation - {self.job.title}"
        message = f"""
Dear {self.user.get_full_name() or self.user.username},

Congratulations! You have been selected for an interview for the {self.job.title} position.

Interview Details:
Date: {interview_datetime.strftime("%B %d, %Y")}
Time: {interview_datetime.strftime("%H:%M")}
Platform: Zoom

Join Zoom Meeting:
{zoom_link}

Please be prepared to:
1. Present your project (5-10 minute presentation)
2. Walk through your code and architecture decisions
3. Answer technical questions about your implementation

Interview Duration: 45-60 minutes

Best regards,
RadiloxRemoteJobs Team
"""
        
        try:
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
                fail_silently=False
            )
            if sent:
                print(f"✓ Interview email sent to {self.user.email}")
            return sent
        except Exception as e:
            print(f"✗ Interview email failed: {str(e)}")
            return False
    
    def _send_interview_completed_email(self):
        """Send interview completion email"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Interview Completed - {self.job.title}"
        message = f"""
Dear {self.user.get_full_name() or self.user.username},

Your interview for the position of {self.job.title} at {self.job.company} has been marked as completed.

Our team will review your interview and project presentation. We will notify you of the outcome soon.

Status: Interview Completed
Position: {self.job.title}
Company: {self.job.company}

Next Steps:
1. Our team will review your interview performance
2. We will notify you of the hiring decision within 3-5 business days
3. If selected, you will receive onboarding information

Thank you for your time and participation.

Best regards,
RadiloxRemoteJobs Team
"""
        
        try:
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
                fail_silently=False
            )
            if sent:
                print(f"✓ Interview completion email sent to {self.user.email}")
            return sent
        except Exception as e:
            print(f"✗ Interview completion email failed: {str(e)}")
            return False
    
    def _send_hiring_email(self, start_date):
        """Send hiring confirmation email immediately"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Congratulations! You're Hired - {self.job.title}"
        message = f"""
Dear {self.user.get_full_name() or self.user.username},

We are delighted to inform you that you have been selected for the {self.job.title} position at {self.job.company}!

Your project presentation and interview were impressive, and we believe you'll be a great addition to our team.

Start Date: {start_date.strftime("%B %d, %Y")}

Next Steps:
1. You will receive your first task assignment before your start date
2. Complete tasks and submit for review
3. Get paid upon successful completion

Welcome to the team!

Best regards,
RadiloxRemoteJobs Team
"""
        
        try:
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
                fail_silently=False
            )
            if sent:
                print(f"✓ Hiring email sent to {self.user.email}")
            return sent
        except Exception as e:
            print(f"✗ Hiring email failed: {str(e)}")
            return False