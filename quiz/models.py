from django.db import models
from django.conf import settings
from jobs.models import Job


class QuizQuestion(models.Model):
    """Quiz questions for job applications"""
    
    QUESTION_TYPES = (
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('text', 'Text Answer'),
    )
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='quiz_questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    question_text = models.TextField()
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_answer = models.CharField(max_length=500)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Quiz Question'
        verbose_name_plural = 'Quiz Questions'
    
    def __str__(self):
        return f"{self.job.title} - {self.question_text[:50]}"
    
    def get_options(self):
        """Return list of option dictionaries"""
        options = []
        if self.option_a:
            options.append({'value': 'A', 'text': self.option_a})
        if self.option_b:
            options.append({'value': 'B', 'text': self.option_b})
        if self.option_c:
            options.append({'value': 'C', 'text': self.option_c})
        if self.option_d:
            options.append({'value': 'D', 'text': self.option_d})
        return options


class QuizResult(models.Model):
    """Quiz results for applicants"""
    
    application = models.OneToOneField('application.Application', on_delete=models.CASCADE, related_name='quiz_result')
    score = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)
    max_score = models.IntegerField(default=100)
    answers = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Quiz Result'
        verbose_name_plural = 'Quiz Results'
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.application.user.username} - {self.application.job.title} - {self.score}%"