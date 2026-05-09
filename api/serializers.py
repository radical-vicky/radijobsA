from rest_framework import serializers
from jobs.models import Job, Application
from tasks.models import Task
from wallet.models import Wallet

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'title', 'company', 'description', 'requirements', 'project_brief', 
                  'salary_range', 'location', 'job_type', 'is_active', 'created_at']

class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    
    class Meta:
        model = Application
        fields = ['id', 'job', 'job_title', 'status', 'cover_letter', 'quiz_score', 
                  'interview_date', 'onboarding_date', 'created_at']
        read_only_fields = ['user', 'created_at']

class TaskSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    
    class Meta:
        model = Task
        fields = ['id', 'job', 'job_title', 'title', 'description', 'budget_amount', 
                  'status', 'deadline', 'submission_url', 'created_at']
        read_only_fields = ['assigned_to', 'created_at']

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance', 'total_earned', 'total_withdrawn']