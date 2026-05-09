from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title', 'company', 'description', 'requirements', 'project_brief',
            'salary_range', 'location', 'job_type', 'experience_level',
            'skills_required', 'image', 'image_url', 'company_logo', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'w-full border rounded-lg p-2'}),
            'requirements': forms.Textarea(attrs={'rows': 5, 'class': 'w-full border rounded-lg p-2'}),
            'project_brief': forms.Textarea(attrs={'rows': 8, 'class': 'w-full border rounded-lg p-2 font-mono'}),
            'skills_required': forms.Textarea(attrs={'rows': 3, 'placeholder': '["Python", "Django", "React"]', 'class': 'w-full border rounded-lg p-2'}),
            'image': forms.ClearableFileInput(attrs={'class': 'w-full border rounded-lg p-2'}),
            'image_url': forms.URLInput(attrs={'class': 'w-full border rounded-lg p-2', 'placeholder': 'https://example.com/image.jpg'}),
            'company_logo': forms.ClearableFileInput(attrs={'class': 'w-full border rounded-lg p-2'}),
        }
        help_texts = {
            'project_brief': 'This is the project candidates must complete before the interview',
            'skills_required': 'Enter skills as a JSON array',
            'image_url': 'External image URL (leave empty if uploading a file)',
        }